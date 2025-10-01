"""Moderation service with model loading, inference, and threshold logic."""

import asyncio
import logging
from typing import Dict, Optional, Any
import threading

from app.config.settings import settings
from app.config.categories import CATEGORIES, DEFAULT_THRESHOLDS

logger = logging.getLogger(__name__)

# Global model instance and lock for thread-safe loading
_model = None
_tokenizer = None
_model_lock = threading.Lock()
_model_load_time: Optional[float] = None
_model_name: Optional[str] = None


async def load_model(model_name: Optional[str] = None) -> tuple:
    """
    Load the moderation model (lazy loading with thread safety).

    Args:
        model_name: Model identifier (defaults to settings.default_model)

    Returns:
        tuple: (model, tokenizer)
    """
    global _model, _tokenizer, _model_load_time, _model_name

    # Use default model if not specified
    if model_name is None:
        model_name = settings.default_model

    # Check if model is already loaded
    if _model is not None and _tokenizer is not None and _model_name == model_name:
        return _model, _tokenizer

    # Acquire lock for thread-safe loading
    with _model_lock:
        # Double-check after acquiring lock
        if _model is not None and _tokenizer is not None and _model_name == model_name:
            return _model, _tokenizer

        logger.info(f"[MODEL] Loading: {model_name}")
        import time

        start = time.perf_counter()

        # Load model in a separate thread to avoid blocking
        def _load():
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            import torch

            tokenizer = AutoTokenizer.from_pretrained(
                model_name, cache_dir=settings.model_cache_dir
            )
            model = AutoModelForSequenceClassification.from_pretrained(
                model_name, cache_dir=settings.model_cache_dir
            )
            model.eval()  # Set to evaluation mode

            # Move to CPU (for simplicity; can be modified for GPU)
            if torch.cuda.is_available():
                model = model.cuda()
                logger.info("Model loaded on GPU")
            else:
                logger.info("Model loaded on CPU")

            return model, tokenizer

        # Run in thread pool to avoid blocking event loop
        _model, _tokenizer = await asyncio.to_thread(_load)
        _model_name = model_name

        end = time.perf_counter()
        _model_load_time = end - start

        logger.info(f"[MODEL] Loaded successfully in {_model_load_time:.2f}s")

    return _model, _tokenizer


def get_model_load_time() -> Optional[float]:
    """Get the time taken to load the model."""
    return _model_load_time


def is_model_loaded() -> bool:
    """Check if model is loaded."""
    return _model is not None and _tokenizer is not None


def get_loaded_model_name() -> Optional[str]:
    """Get the name of the loaded model."""
    return _model_name


async def run_inference(text: str, model_name: Optional[str] = None) -> Dict[str, float]:
    """
    Run inference on text input.

    Args:
        text: Text to moderate
        model_name: Model identifier (optional)

    Returns:
        Dict[str, float]: Category scores (0.0-1.0)
    """
    # Load model if needed
    model, tokenizer = await load_model(model_name)

    # Run inference in thread pool
    def _inference():
        import torch

        # Tokenize input
        inputs = tokenizer(
            text, return_tensors="pt", truncation=True, max_length=512, padding=True
        )

        # Move to same device as model
        device = next(model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}

        # Run inference
        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits

        # Apply sigmoid to get probabilities
        probabilities = torch.sigmoid(logits).cpu().numpy()[0]

        # Map toxic-bert labels to OpenAI moderation categories
        # toxic-bert outputs: [toxic, severe_toxic, obscene, threat, insult, identity_hate]
        # Our categories: [harassment, hate, profanity, sexual, spam, violence]

        # Mapping logic based on label semantics:
        # - toxic/severe_toxic/insult → harassment (aggressive behavior)
        # - identity_hate → hate (targeted discrimination)
        # - obscene → profanity (inappropriate language)
        # - threat → violence (threatening behavior)
        # Note: toxic-bert doesn't have sexual/spam, so we derive them from other signals

        toxic_score = float(probabilities[0]) if len(probabilities) > 0 else 0.0
        severe_toxic_score = float(probabilities[1]) if len(probabilities) > 1 else 0.0
        obscene_score = float(probabilities[2]) if len(probabilities) > 2 else 0.0
        threat_score = float(probabilities[3]) if len(probabilities) > 3 else 0.0
        insult_score = float(probabilities[4]) if len(probabilities) > 4 else 0.0
        identity_hate_score = float(probabilities[5]) if len(probabilities) > 5 else 0.0

        scores = {
            # Harassment: combination of toxic, insult, and severe_toxic
            "harassment": max(insult_score, (toxic_score + severe_toxic_score) / 2),

            # Hate: primarily identity_hate, boosted by severe_toxic
            "hate": max(identity_hate_score, severe_toxic_score * 0.8),

            # Profanity: obscene language
            "profanity": obscene_score,

            # Sexual: derive from obscene when combined with low threat/insult
            # (obscene language that's not threatening/insulting is often sexual)
            "sexual": obscene_score * 0.6 if threat_score < 0.5 and insult_score < 0.5 else obscene_score * 0.3,

            # Violence: threat-based content
            "violence": threat_score,

            # Spam: derive from toxic patterns with low semantic content
            # (repetitive toxic content with low specific category scores)
            "spam": toxic_score * 0.3 if all(s < 0.4 for s in [insult_score, threat_score, obscene_score]) else 0.0,
        }

        return scores

    scores = await asyncio.to_thread(_inference)
    return scores


def apply_thresholds(
    scores: Dict[str, float],
    custom_thresholds: Optional[Dict[str, float]] = None,
) -> tuple[bool, Dict[str, bool]]:
    """
    Apply thresholds to scores to determine if content is flagged.

    Args:
        scores: Category scores (0.0-1.0)
        custom_thresholds: Optional custom thresholds per category

    Returns:
        tuple: (flagged, category_flags)
            - flagged: True if any category exceeds threshold
            - category_flags: Boolean flags per category
    """
    # Start with default thresholds
    thresholds = settings.default_thresholds.copy()

    # Override with custom thresholds if provided
    if custom_thresholds:
        thresholds.update(custom_thresholds)

    # Apply thresholds
    category_flags = {}
    flagged = False

    for category in CATEGORIES:
        score = scores.get(category, 0.0)
        threshold = thresholds.get(category, DEFAULT_THRESHOLDS.get(category, 0.5))
        is_flagged = score >= threshold
        category_flags[category] = is_flagged

        if is_flagged:
            flagged = True

    return flagged, category_flags


async def moderate_text(
    text: str,
    model_name: Optional[str] = None,
    custom_thresholds: Optional[Dict[str, float]] = None,
) -> tuple[bool, Dict[str, bool], Dict[str, float]]:
    """
    Moderate a single text input.

    Args:
        text: Text to moderate
        model_name: Model identifier (optional)
        custom_thresholds: Optional custom thresholds per category

    Returns:
        tuple: (flagged, category_flags, scores)
    """
    # Run inference
    scores = await run_inference(text, model_name)

    # Apply thresholds
    flagged, category_flags = apply_thresholds(scores, custom_thresholds)

    return flagged, category_flags, scores