"""Image moderation service with validation and preprocessing."""

import asyncio
import base64
import hashlib
import io
import logging
from typing import Dict, Optional, Tuple
from PIL import Image
import aiohttp

from app.config.settings import settings

logger = logging.getLogger(__name__)

# Configuration
MAX_IMAGE_SIZE_MB = 10
MAX_DIMENSION = 4096
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP", "GIF"}
URL_TIMEOUT_SECONDS = 10

_image_model = None
_image_processor = None
_model_load_time: Optional[float] = None
_http_session: Optional[aiohttp.ClientSession] = None


async def get_http_session() -> aiohttp.ClientSession:
    """Get or create HTTP session for image downloads."""
    global _http_session
    if _http_session is None or _http_session.closed:
        timeout = aiohttp.ClientTimeout(total=URL_TIMEOUT_SECONDS)
        _http_session = aiohttp.ClientSession(timeout=timeout)
    return _http_session


async def close_http_session():
    """Close HTTP session (call on shutdown)."""
    global _http_session
    if _http_session and not _http_session.closed:
        await _http_session.close()


def compute_image_hash(image_bytes: bytes) -> str:
    """Compute SHA256 hash of image for caching."""
    return hashlib.sha256(image_bytes).hexdigest()[:16]


async def fetch_image_from_url(url: str) -> Tuple[bytes, str]:
    """
    Fetch image from URL.

    Returns:
        (image_bytes, content_hash)

    Raises:
        ValueError: If URL is invalid or fetch fails
    """
    session = await get_http_session()

    try:
        async with session.get(url) as response:
            if response.status != 200:
                raise ValueError(f"Failed to fetch image: HTTP {response.status}")

            content_type = response.headers.get("Content-Type", "")
            if not content_type.startswith("image/"):
                raise ValueError(f"URL does not point to an image: {content_type}")

            image_bytes = await response.read()

            # Check size
            size_mb = len(image_bytes) / (1024 * 1024)
            if size_mb > MAX_IMAGE_SIZE_MB:
                raise ValueError(f"Image too large: {size_mb:.2f}MB (max {MAX_IMAGE_SIZE_MB}MB)")

            content_hash = compute_image_hash(image_bytes)
            return image_bytes, content_hash

    except asyncio.TimeoutError:
        raise ValueError(f"Timeout fetching image from URL")
    except Exception as e:
        raise ValueError(f"Failed to fetch image: {str(e)}")


def decode_base64_image(base64_str: str) -> Tuple[bytes, str]:
    """
    Decode base64 image string.

    Supports:
    - Plain base64: "iVBORw0KGgo..."
    - Data URI: "data:image/png;base64,iVBORw0KGgo..."

    Returns:
        (image_bytes, content_hash)
    """
    # Handle data URI format
    if base64_str.startswith("data:"):
        if ";base64," in base64_str:
            base64_str = base64_str.split(";base64,")[1]
        else:
            raise ValueError("Invalid data URI format")

    try:
        image_bytes = base64.b64decode(base64_str)

        # Check size
        size_mb = len(image_bytes) / (1024 * 1024)
        if size_mb > MAX_IMAGE_SIZE_MB:
            raise ValueError(f"Image too large: {size_mb:.2f}MB (max {MAX_IMAGE_SIZE_MB}MB)")

        content_hash = compute_image_hash(image_bytes)
        return image_bytes, content_hash

    except Exception as e:
        raise ValueError(f"Failed to decode base64 image: {str(e)}")


def validate_and_preprocess_image(image_bytes: bytes) -> Image.Image:
    """
    Validate and preprocess image.

    Returns:
        PIL Image (RGB, resized to 224x224 for model input)

    Raises:
        ValueError: If image is invalid
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))

        # Validate format
        if image.format not in ALLOWED_FORMATS:
            raise ValueError(f"Unsupported format: {image.format}")

        # Validate dimensions (before resize)
        width, height = image.size
        if width > MAX_DIMENSION or height > MAX_DIMENSION:
            raise ValueError(f"Image dimensions too large: {width}x{height} (max {MAX_DIMENSION}x{MAX_DIMENSION})")

        # Convert to RGB (handle RGBA, grayscale, etc.)
        if image.mode != "RGB":
            image = image.convert("RGB")

        # OPTIMIZATION 3: Resize to model's native input size (224x224)
        # This is much faster than processing large images
        if image.size != (224, 224):
            original_size = image.size
            image = image.resize((224, 224), Image.Resampling.LANCZOS)
            logger.debug(f"Resized image from {original_size} to 224x224 for inference")

        return image

    except Exception as e:
        raise ValueError(f"Invalid image: {str(e)}")


async def load_image_model(model_name: Optional[str] = None):
    """Load image moderation model (lazy loading)."""
    global _image_model, _image_processor, _model_load_time

    if _image_model is not None:
        return _image_model, _image_processor

    if model_name is None:
        model_name = settings.default_image_model

    logger.info(f"[IMAGE MODEL] Loading: {model_name}")

    import time
    start = time.perf_counter()

    def _load():
        from transformers import AutoModelForImageClassification, ViTImageProcessor
        import torch

        # Load processor and model separately for compatibility
        try:
            processor = ViTImageProcessor.from_pretrained(
                model_name, cache_dir=settings.model_cache_dir
            )
        except Exception:
            # Fallback: create processor manually
            processor = ViTImageProcessor(size=224)

        model = AutoModelForImageClassification.from_pretrained(
            model_name, cache_dir=settings.model_cache_dir
        )
        model.eval()

        if torch.cuda.is_available():
            model = model.cuda()
            logger.info("[IMAGE MODEL] Loaded on GPU")
        else:
            logger.info("[IMAGE MODEL] Loaded on CPU")

        return model, processor

    _image_model, _image_processor = await asyncio.to_thread(_load)

    end = time.perf_counter()
    _model_load_time = end - start

    logger.info(f"[IMAGE MODEL] Loaded successfully in {_model_load_time:.2f}s")

    return _image_model, _image_processor


def is_image_model_loaded() -> bool:
    """Check if image model is loaded."""
    return _image_model is not None


def get_loaded_image_model_name() -> Optional[str]:
    """Get loaded image model name."""
    if _image_model is None:
        return None
    return settings.default_image_model


def get_image_model_load_time() -> Optional[float]:
    """Get image model load time."""
    return _model_load_time


async def run_image_inference(image: Image.Image, model_name: Optional[str] = None) -> Dict[str, float]:
    """
    Run inference on preprocessed image.

    Returns:
        Dict with normalized scores for our categories
    """
    model, processor = await load_image_model(model_name)

    def _inference():
        import torch

        # Preprocess
        inputs = processor(images=image, return_tensors="pt")

        # Move to device
        device = next(model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}

        # Inference
        with torch.no_grad():
            outputs = model(**inputs)
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1)

        # Map model outputs to our categories
        # Falconsai model labels: id2label = {0: "normal", 1: "nsfw"}
        nsfw_score = float(probs[0][1])  # Index 1 is "nsfw"

        # Map to our category schema
        scores = {
            "sexual": nsfw_score,
        }

        return scores

    return await asyncio.to_thread(_inference)


async def moderate_image(
    image_input: str,
    model_name: Optional[str] = None,
) -> Tuple[Dict[str, float], str]:
    """
    Moderate image from URL or base64.

    Args:
        image_input: URL or base64 string
        model_name: Optional model override

    Returns:
        (scores_dict, content_hash)

    Raises:
        ValueError: If image is invalid or processing fails
    """
    # Step 1: Fetch/decode image
    if image_input.startswith("http://") or image_input.startswith("https://"):
        image_bytes, content_hash = await fetch_image_from_url(image_input)
    else:
        image_bytes, content_hash = decode_base64_image(image_input)

    # Step 2: Validate and preprocess
    image = validate_and_preprocess_image(image_bytes)

    # Step 3: Run inference
    scores = await run_image_inference(image, model_name)

    return scores, content_hash
