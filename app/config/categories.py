"""Category mappings and default thresholds for moderation."""

from typing import Dict

# Default category thresholds
DEFAULT_THRESHOLDS: Dict[str, float] = {
    "harassment": 0.7,
    "hate": 0.7,
    "profanity": 0.6,
    "sexual": 0.7,
    "spam": 0.8,
    "violence": 0.6,
}

# Category list
CATEGORIES = list(DEFAULT_THRESHOLDS.keys())

# Model category mappings for toxic-bert
# Maps model output labels to our standard categories
TOXIC_BERT_CATEGORY_MAP = {
    "toxic": "harassment",
    "severe_toxic": "hate",
    "obscene": "profanity",
    "threat": "violence",
    "insult": "harassment",
    "identity_hate": "hate",
}