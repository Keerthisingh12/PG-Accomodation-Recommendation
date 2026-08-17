"""
src/sentiment_analyzer.py
─────────────────────────
Converts a free-text PG review into a numeric sentiment score [0.0, 1.0]
using the HuggingFace Transformers model:

    cardiffnlp/twitter-roberta-base-sentiment

Model labels:
    LABEL_0 → Negative
    LABEL_1 → Neutral
    LABEL_2 → Positive

Star mapping (as requested):
    POSITIVE  + high confidence (≥ 0.8) → 5 stars  → score 1.00
    POSITIVE  + low  confidence (< 0.8) → 4 stars  → score 0.75
    NEUTRAL                             → 3 stars  → score 0.50
    NEGATIVE  + low  confidence (< 0.8) → 2 stars  → score 0.25
    NEGATIVE  + high confidence (≥ 0.8) → 1 star   → score 0.00

Public API (unchanged):
    analyze(text: str)           -> float  [0.0, 1.0]
    sentiment_label(score: float)-> str    "Poor" / "Average" / "Good" / "Excellent"
    star_equivalent(score: float)-> float  1.0 – 5.0
"""

from transformers import pipeline as hf_pipeline

# ── Model config ──────────────────────────────────────────────────────────────
_MODEL_NAME  = "cardiffnlp/twitter-roberta-base-sentiment"
_HIGH_CONF   = 0.8   # threshold that separates 4★ from 5★ (and 2★ from 1★)

# Label names emitted by the model
_LABEL_NEGATIVE = "LABEL_0"
_LABEL_NEUTRAL  = "LABEL_1"
_LABEL_POSITIVE = "LABEL_2"

# ── Lazy-loaded pipeline (loaded once on first call, not at import time) ──────
_pipeline = None

def _get_pipeline():
    """Return the singleton sentiment pipeline, loading it on first call."""
    global _pipeline
    if _pipeline is None:
        _pipeline = hf_pipeline(
            "sentiment-analysis",
            model=_MODEL_NAME,
            truncation=True,    # reviews > 512 tokens are silently truncated
            max_length=512,
        )
    return _pipeline


# ── Score mapping ─────────────────────────────────────────────────────────────

def _label_conf_to_score(label: str, confidence: float) -> float:
    """
    Map (label, confidence) → a continuous sentiment score in [0.0, 1.0].

    Discrete star bands:
        POSITIVE  high  → 1.00  (5 stars)
        POSITIVE  low   → 0.75  (4 stars)
        NEUTRAL         → 0.50  (3 stars)
        NEGATIVE  low   → 0.25  (2 stars)
        NEGATIVE  high  → 0.00  (1 star)
    """
    if label == _LABEL_POSITIVE:
        return 1.00 if confidence >= _HIGH_CONF else 0.75
    if label == _LABEL_NEUTRAL:
        return 0.50
    # LABEL_0 → Negative
    return 0.00 if confidence >= _HIGH_CONF else 0.25


# ── Public API ────────────────────────────────────────────────────────────────

def analyze(text: str) -> float:
    """
    Run the HuggingFace sentiment model on *text* and return a score in [0, 1].

    Returns 0.5 (neutral) for empty / whitespace-only input.
    """
    if not text or not text.strip():
        return 0.5

    pipe   = _get_pipeline()
    result = pipe(text.strip())[0]          # e.g. {"label": "LABEL_2", "score": 0.93}

    label      = result["label"]
    confidence = result["score"]

    return round(_label_conf_to_score(label, confidence), 4)


def sentiment_label(score: float) -> str:
    """
    Map a [0, 1] sentiment score to a human-readable label.

    0.00       → "Poor"     (1 star)
    0.25       → "Average"  (2 stars)
    0.50       → "Good"     (3 stars)
    0.75       → "Good"     (4 stars)
    1.00       → "Excellent"(5 stars)
    """
    if score >= 0.90:
        return "Excellent"
    if score >= 0.60:
        return "Good"
    if score >= 0.40:
        return "Average"
    return "Poor"


def star_equivalent(score: float) -> float:
    """
    Map sentiment score [0, 1] → star rating [1.0, 5.0].
    Used to blend text sentiment into the recommendation pipeline.
    """
    return round(1.0 + score * 4.0, 2)
