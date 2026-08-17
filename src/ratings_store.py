"""
src/ratings_store.py
─────────────────────
Handles persistent user ratings AND text reviews stored in PostgreSQL.

Provides:
  - add_rating(pg_id, rating)           → insert into ratings table
  - get_stats(pg_id)                    → {average_rating, rating_count}
  - get_all_stats()                     → dict keyed by pg_id
  - compute_confidence(...)             → consistency × (avg / 5)
  - compute_trust(...)                  → log(1 + count) × (avg / 5)

  Text reviews:
  - add_review(pg_id, text)             → analyze sentiment, insert into reviews table
  - get_review_stats(pg_id)             → {avg_sentiment, review_count, reviews: [...]}
  - get_all_review_stats()              → dict keyed by pg_id
"""

import math
import pandas as pd
from sqlalchemy import create_engine
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATABASE_URL

from src.sentiment_analyzer import analyze as _analyze_sentiment, sentiment_label, star_equivalent

# ── Defaults when a PG has zero user ratings ──────────────────────────────
_DEFAULT_AVG   = 3.5   # neutral starting average
_DEFAULT_COUNT = 0

engine = create_engine(DATABASE_URL)

# ─────────────────────────────────────────────────────────────────────────
# STAR RATINGS — WRITE
# ─────────────────────────────────────────────────────────────────────────

def add_rating(pg_id: int, rating: int) -> dict:
    """
    Append a new star rating to the database.

    Args:
        pg_id:  Integer PG identifier (matches PG_ID column in dataset)
        rating: Integer 1–5

    Returns:
        Updated stats dict for this PG: {average_rating, rating_count}

    Raises:
        ValueError: If rating is not in 1–5 range.
    """
    if not (1 <= int(rating) <= 5):
        raise ValueError(f"Rating must be 1–5, got {rating}")

    row = pd.DataFrame([{"pg_id": int(pg_id), "rating": int(rating)}])
    row.to_sql("ratings", engine, if_exists="append", index=False)

    return get_stats(pg_id)


# ─────────────────────────────────────────────────────────────────────────
# STAR RATINGS — READ / AGGREGATE
# ─────────────────────────────────────────────────────────────────────────

def _load() -> pd.DataFrame:
    """Load the ratings from the database, returning an empty DataFrame if missing."""
    try:
        df = pd.read_sql("SELECT * FROM ratings", engine)
    except Exception:
        df = pd.DataFrame(columns=["pg_id", "rating"])
    
    if df.empty:
        return df
    df["pg_id"]  = df["pg_id"].astype(int)
    df["rating"] = df["rating"].astype(int)
    return df


def get_stats(pg_id: int) -> dict:
    """
    Compute average_rating and rating_count for a single PG.

    Returns default values if no ratings exist yet.
    """
    df = _load()
    subset = df[df["pg_id"] == int(pg_id)]

    if subset.empty:
        return {
            "average_rating": _DEFAULT_AVG,
            "rating_count":   _DEFAULT_COUNT,
        }

    return {
        "average_rating": round(float(subset["rating"].mean()), 2),
        "rating_count":   int(len(subset)),
    }


def get_all_stats() -> dict:
    """
    Return a dict of stats for ALL PGs that have at least one rating.

    Returns:
        { pg_id (int): {"average_rating": float, "rating_count": int} }
    """
    df = _load()
    if df.empty:
        return {}

    grouped = df.groupby("pg_id")["rating"].agg(["mean", "count"]).reset_index()
    grouped.columns = ["pg_id", "average_rating", "rating_count"]

    result = {}
    for _, row in grouped.iterrows():
        result[int(row["pg_id"])] = {
            "average_rating": round(float(row["average_rating"]), 2),
            "rating_count":   int(row["rating_count"]),
        }
    return result


# ─────────────────────────────────────────────────────────────────────────
# TEXT REVIEWS — WRITE
# ─────────────────────────────────────────────────────────────────────────

def add_review(pg_id: int, review_text: str) -> dict:
    """
    Analyze sentiment of a text review and persist it to the database.

    Args:
        pg_id:       Integer PG identifier
        review_text: Free-text review string

    Returns:
        {
            "sentiment_score": float,      # 0.0–1.0
            "sentiment_label": str,        # "Poor"/"Average"/"Good"/"Excellent"
            "star_equivalent": float,      # 1.0–5.0
            "avg_sentiment":   float,      # updated average for this PG
            "review_count":    int,
        }

    Raises:
        ValueError: If review_text is empty.
    """
    text = (review_text or "").strip()
    if not text:
        raise ValueError("Review text cannot be empty.")
    if len(text) < 5:
        raise ValueError("Review is too short (minimum 5 characters).")

    score = _analyze_sentiment(text)

    row = pd.DataFrame([{
        "pg_id":           int(pg_id),
        "review_text":     text,
        "sentiment_score": score,
    }])

    row.to_sql("reviews", engine, if_exists="append", index=False)

    stats = get_review_stats(pg_id)
    return {
        "sentiment_score": score,
        "sentiment_label": sentiment_label(score),
        "star_equivalent": star_equivalent(score),
        **stats,
    }


# ─────────────────────────────────────────────────────────────────────────
# TEXT REVIEWS — READ / AGGREGATE
# ─────────────────────────────────────────────────────────────────────────

def _load_reviews() -> pd.DataFrame:
    """Load reviews from database, returning an empty DataFrame if missing."""
    try:
        df = pd.read_sql("SELECT * FROM reviews", engine)
    except Exception:
        df = pd.DataFrame(columns=["pg_id", "review_text", "sentiment_score"])
        
    if df.empty:
        return df
    df["pg_id"]           = df["pg_id"].astype(int)
    df["sentiment_score"] = df["sentiment_score"].astype(float)
    return df


def get_review_stats(pg_id: int) -> dict:
    """
    Return sentiment stats + recent reviews for a single PG.

    Returns:
        {
            "avg_sentiment": float,   # 0.0–1.0, or 0.5 if no reviews
            "review_count":  int,
            "reviews":       list of {"text": str, "sentiment_score": float,
                                      "sentiment_label": str}
        }
    """
    df = _load_reviews()
    subset = df[df["pg_id"] == int(pg_id)]

    if subset.empty:
        return {
            "avg_sentiment": 0.5,
            "review_count":  0,
            "reviews":       [],
        }

    avg = round(float(subset["sentiment_score"].mean()), 4)
    reviews = [
        {
            "text":            row["review_text"],
            "sentiment_score": round(float(row["sentiment_score"]), 4),
            "sentiment_label": sentiment_label(float(row["sentiment_score"])),
        }
        for _, row in subset.iterrows()
    ]
    # Return up to last 5 reviews (most recent last)
    return {
        "avg_sentiment": avg,
        "review_count":  int(len(subset)),
        "reviews":       reviews[-5:],
    }


def get_all_review_stats() -> dict:
    """
    Return avg_sentiment and review_count for ALL PGs that have reviews.

    Returns:
        { pg_id (int): {"avg_sentiment": float, "review_count": int} }
    """
    df = _load_reviews()
    if df.empty:
        return {}

    grouped = df.groupby("pg_id")["sentiment_score"].agg(["mean", "count"]).reset_index()
    grouped.columns = ["pg_id", "avg_sentiment", "review_count"]

    result = {}
    for _, row in grouped.iterrows():
        result[int(row["pg_id"])] = {
            "avg_sentiment": round(float(row["avg_sentiment"]), 4),
            "review_count":  int(row["review_count"]),
        }
    return result


# ─────────────────────────────────────────────────────────────────────────
# TRUST / CONFIDENCE FORMULAS
# ─────────────────────────────────────────────────────────────────────────

def compute_confidence(rating_count: int, average_rating: float) -> float:
    """
    confidence = consistency × (avg / 5)
    consistency = rating_count / (rating_count + 10)

    Approaches 1.0 as more ratings accumulate.
    """
    consistency = rating_count / (rating_count + 10)
    return round(consistency * (average_rating / 5.0), 4)


def compute_trust(rating_count: int, average_rating: float) -> float:
    """
    trust = log(1 + rating_count) × (avg / 5)

    Grows logarithmically with more ratings.
    Normalised so 100 ratings ≈ max ~0.921.
    """
    return round(math.log1p(rating_count) * (average_rating / 5.0), 4)
