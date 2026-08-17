"""
src/recommender.py
───────────────────
Responsible for:
  - Hard filtering (availability, budget, gender)
  - Scoring PGs using weighted squared-distance formula
  - Fuzzy location matching bonus
  - Ranking and normalizing scores to a [1.0, 5.0] rating
  - Trust-aware scoring using real user ratings (ratings_store)
"""

import os
import sys
import math
import numpy as np
import pandas as pd
from rapidfuzz import fuzz

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    DEFAULT_WEIGHTS,
    LOCATION_WEIGHT,
    LOCATION_FUZZY_THRESHOLD,
    GENDER_COMPAT,
    DEFAULT_TOP_N,
)
from src.ratings_store import (
    get_all_stats,
    get_all_review_stats,
    compute_confidence,
    compute_trust,
    _DEFAULT_AVG,
    _DEFAULT_COUNT,
)


# ─────────────────────────────────────────────────────────────
# HARD FILTER
# ─────────────────────────────────────────────────────────────

def hard_filter(df: pd.DataFrame, budget: float, gender: int, sharing: str = "Any") -> pd.DataFrame:
    """
    Remove PGs that are definitively invalid before scoring.

    Criteria:
      - Availability == 1 (not full)
      - Original_Rent <= budget  (raw ₹ vs raw ₹  — BUG FIX)
      - Gender is compatible with user preference  (BUG FIX: Co-ed is valid
        for Boys/Girls users; old code did exact equality match only)

    Args:
        df:      Preprocessed DataFrame (must have Original_Rent column)
        budget:  User's raw budget in ₹
        gender:  Encoded gender preference (0=Boys, 1=Girls, 2=Co-ed)

    Returns:
        Filtered DataFrame copy.
    """
    valid_genders = GENDER_COMPAT.get(gender, [gender])

    df_filtered = df[
        (df["Availability"] == 1) &
        (df["Original_Rent"] <= budget) &           # raw ₹ comparison — fixed
        (df["Gender"].isin(valid_genders))           # inclusive gender match — fixed
    ].copy()

    if sharing != "Any":
        df_filtered = df_filtered[df_filtered["Sharing"] == sharing].copy()

    return df_filtered


# ─────────────────────────────────────────────────────────────
# SCORING
# ─────────────────────────────────────────────────────────────

def score_pgs(
    df: pd.DataFrame,
    user_input: dict,
    user_location: str,
    weights: dict = None,
) -> pd.DataFrame:
    """
    Score each PG using Weighted Euclidean Distance from user preferences.

    Formula per PG:
        distance_score = sqrt( Σ  w_i * (pg_i - user_i)² )
        location_bonus = LOCATION_WEIGHT * fuzzy_ratio(pg_loc, user_loc)
        final_score    = distance_score - location_bonus

    Lower final_score means better match.

    Args:
        df:            Filtered + preprocessed DataFrame
        user_input:    Dict of normalized feature values  {feature: value}
        user_location: User's preferred location string (lowercased)
        weights:       Optional custom weights dict (defaults to config.DEFAULT_WEIGHTS)

    Returns:
        DataFrame with distance_score, location_match, and final_score columns added.
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    df_copy = df.copy()

    # ── Weighted squared distance ─────────────────────────────
    squared_sum = pd.Series(0.0, index=df_copy.index)
    # Convert distance → score (lower distance = better)
    df_copy["distance_score"] = 1 / (1 + df_copy["Distance_From_Center_KM"])

    for feature, weight in weights.items():
        if feature == "Distance_From_Center_KM":
            # Convert distance → penalty (closer = smaller penalty)
            diff = 1 - df_copy["distance_score"]
        elif feature in df_copy.columns and feature in user_input:
            diff = df_copy[feature] - user_input[feature]
        else:
            continue

        squared_sum += weight * (diff ** 2)

    df_copy["distance_score"] = np.sqrt(squared_sum)

    # ── Fuzzy location matching ──────────────────────────────
    #   BUG FIX: old code used exact string match → -0.2 bonus or 0
    #   New: partial ratio gives a continuous 0.0–1.0 similarity score
    df_copy["location_match"] = df_copy["Location"].apply(
        lambda loc: fuzz.partial_ratio(str(loc), user_location) / 100.0
    )

    # ── Final score ──────────────────────────────────────────
    df_copy["final_score"] = (
        df_copy["distance_score"] - (LOCATION_WEIGHT * df_copy["location_match"])
    )

    return df_copy


# ─────────────────────────────────────────────────────────────
# LEGACY UNCERTAINTY HELPER (kept for reference)
# ─────────────────────────────────────────────────────────────

def compute_uncertainty(ratings: list) -> float:
    """Compute rating dispersion (uncertainty). δ = average(|r - mean_rating|)"""
    if not ratings:
        return 0.0
    mean_r = sum(ratings) / len(ratings)
    return sum(abs(r - mean_r) for r in ratings) / len(ratings)

# ─────────────────────────────────────────────────────────────
# RANKING & RATING
# ─────────────────────────────────────────────────────────────

def rank_and_rate(df: pd.DataFrame, top_n: int = DEFAULT_TOP_N) -> pd.DataFrame:
    """
    Sort by location tier FIRST, then by normalized_score within each tier.

    Location tiers (based on fuzzy match score already computed in score_pgs):
      Tier 2 — Strong match  : location_match >= 0.75  (user's area / very close)
      Tier 1 — Partial match : location_match >= 0.40  (nearby / same zone)
      Tier 0 — No match      : location_match <  0.40  (different part of city)

    Sorting key: (location_tier DESC, normalized_score DESC)
    This guarantees a Rt Nagar PG always beats a Hebbal PG when user searched
    for Rt Nagar, even if the Hebbal PG has more/better user ratings.

    Rating formula:
        match_rating = (normalized_score * 4) + 1   → always in [1.0, 5.0]
    """
    df = df.copy()

    # Assign location tier
    def _tier(loc_match: float) -> int:
        if loc_match >= 0.75:
            return 2
        if loc_match >= 0.40:
            return 1
        return 0

    if "location_match" in df.columns:
        df["location_tier"] = df["location_match"].apply(_tier)
    else:
        df["location_tier"] = 0

    # Sort: location tier first, then match quality
    df = df.sort_values(
        ["location_tier", "normalized_score"], ascending=[False, False]
    )

    # Rating always between 1.0 and 5.0
    df["match_rating"] = (df["normalized_score"] * 4 + 1).round(1)

    df["Rank"] = range(1, len(df) + 1)

    def generate_reason(row):
        tier  = row.get("location_tier", 0)
        conf  = row.get("Confidence_Score", 0)
        trust = row.get("Trust_Score", 0)
        n     = row.get("rating_count", 0)
        parts = []
        if tier == 2:
            parts.append("Exact location match")
        elif tier == 1:
            parts.append("Nearby location")
        if conf >= 0.7:
            parts.append("high rating consistency")
        elif conf >= 0.55:
            parts.append("moderate rating consistency")
        if n > 0 and trust >= 0.7:
            parts.append("high trust score")
        if not parts:
            return "Matches your preferences"
        return ", ".join(parts) + " and matches your preferences"

    df["Why_Matched"] = df.apply(generate_reason, axis=1)

    return df.head(top_n)


# ─────────────────────────────────────────────────────────────
# FULL PIPELINE (single entry point)
# ─────────────────────────────────────────────────────────────

def recommend(
    df: pd.DataFrame,
    user_input: dict,
    user_location: str,
    budget: float,
    gender: int,
    top_n: int = DEFAULT_TOP_N,
    weights: dict = None,
    sharing: str = "Any",
    db_stats: dict = None,
    review_stats: dict = None,
) -> pd.DataFrame:
    """
    Run the complete recommendation pipeline.

    Steps:
      1. Hard filter (availability + budget + gender)
      2. Score using weighted Euclidean distance + fuzzy location bonus
      3. Rank and assign ratings

    Args:
        df:            Preprocessed PG DataFrame
        user_input:    Normalized user feature dict
        user_location: Preferred location (lowercased string)
        budget:        Raw budget in ₹
        gender:        Encoded gender preference (0/1/2)
        top_n:         Number of results to return
        weights:       Custom feature weights dict (optional)

    Returns:
        Ranked DataFrame of top-N recommended PGs.

    Raises:
        ValueError: If no PGs match the hard filter criteria.
    """
    df_filtered = hard_filter(df, budget, gender, sharing)

    if df_filtered.empty:
        return "No suitable PG found based on your preferences. Try adjusting filters."

    df_scored = score_pgs(df_filtered, user_input, user_location, weights)

    # 1. Normalize distance into a base_score where HIGHER is BETTER (0 to 1)
    max_d = df_scored["final_score"].max()
    min_d = df_scored["final_score"].min()
    df_scored["base_score"] = 1.0 - ((df_scored["final_score"] - min_d) / (max_d - min_d + 1e-9))

    # 2. Merge in REAL user ratings from ratings_store (or external db_stats)
    # NOTE: JSON keys arrive as strings; normalize to int so lookups always work
    def _normalize_keys(d: dict) -> dict:
        if d is None:
            return {}
        return {int(k): v for k, v in d.items()}

    raw_stats = db_stats if db_stats is not None else get_all_stats()
    all_stats = _normalize_keys(raw_stats)

    def _get_avg(pg_id):
        return all_stats.get(int(pg_id), {}).get("average_rating", _DEFAULT_AVG)

    def _get_cnt(pg_id):
        return all_stats.get(int(pg_id), {}).get("rating_count", _DEFAULT_COUNT)

    df_scored["average_rating"] = df_scored["PG_ID"].apply(_get_avg)
    df_scored["rating_count"]   = df_scored["PG_ID"].apply(_get_cnt)

    # 2b. Merge text-review sentiment scores
    #
    #    avg_sentiment is in [0, 1] where:
    #      0.0 = very negative reviews
    #      0.5 = neutral (default when no reviews)
    #      1.0 = very positive reviews
    #
    raw_review_stats = review_stats if review_stats is not None else get_all_review_stats()
    all_review_stats = _normalize_keys(raw_review_stats)

    def _get_sentiment(pg_id):
        return all_review_stats.get(int(pg_id), {}).get("avg_sentiment", 0.5)

    def _get_review_count(pg_id):
        return all_review_stats.get(int(pg_id), {}).get("review_count", 0)

    df_scored["avg_sentiment"]  = df_scored["PG_ID"].apply(_get_sentiment)
    df_scored["review_count"]   = df_scored["PG_ID"].apply(_get_review_count)

    # 3. Compute a single trust_multiplier per PG.
    #
    #    Now blends BOTH star ratings AND text-review sentiment:
    #
    #    Star rating component:
    #      weight_r = n / (n + 10)              # 0→0, grows to 1 as n→∞
    #      signal_r = (avg - 3.0) / 2.0         # -1 (avg=1) → 0 (avg=3) → +1 (avg=5)
    #      star_mult = clip(0.5 + 0.5 × weight_r × signal_r, 0.1, 1.0)
    #
    #    Text-review sentiment component:
    #      weight_t = review_count / (review_count + 5)   # weights up faster (fewer needed)
    #      signal_t = (avg_sentiment - 0.5) × 2           # -1 → 0 → +1
    #      text_mult = clip(0.5 + 0.5 × weight_t × signal_t, 0.1, 1.0)
    #
    #    Combined multiplier (70% star ratings, 30% text sentiment):
    #      trust_multiplier = 0.70 × star_mult + 0.30 × text_mult
    #      (when no reviews exist text_mult = 0.5 → contribution = 0.15 neutral)
    #
    #    Examples:
    #      n=0,  avg=3.5 (default), 0 reviews → 0.50 × 0.70 + 0.50 × 0.30 = 0.50 (neutral)
    #      n=10, avg=5.0, 0 reviews → 0.75 × 0.70 + 0.50 × 0.30 = 0.675
    #      n=10, avg=5.0, 3 reviews Excellent → 0.75 × 0.70 + 0.85 × 0.30 ≈ 0.78  (big boost)
    #      n=10, avg=5.0, 3 reviews Poor → 0.75 × 0.70 + 0.15 × 0.30 ≈ 0.57  (penalty)

    def _star_multiplier(n: int, avg: float) -> float:
        if n == 0:
            return 0.5
        weight = n / (n + 10)
        signal = (avg - 3.0) / 2.0
        return max(0.1, min(1.0, 0.5 + 0.5 * weight * signal))

    def _text_multiplier(review_count: int, avg_sentiment: float) -> float:
        if review_count == 0:
            return 0.5  # neutral — no reviews yet
        weight = review_count / (review_count + 5)
        signal = (avg_sentiment - 0.5) * 2.0   # -1 → +1
        return max(0.1, min(1.0, 0.5 + 0.5 * weight * signal))

    def _trust_multiplier(n: int, avg: float, r_cnt: int, sent: float) -> float:
        sm = _star_multiplier(n, avg)
        tm = _text_multiplier(r_cnt, sent)
        return round(0.70 * sm + 0.30 * tm, 4)

    df_scored["trust_multiplier"] = df_scored.apply(
        lambda r: _trust_multiplier(
            int(r["rating_count"]), float(r["average_rating"]),
            int(r["review_count"]),  float(r["avg_sentiment"]),
        ), axis=1
    )
    # Keep separate columns for display on the card
    df_scored["Confidence_Score"] = df_scored["trust_multiplier"]   # shown as "Confidence"
    df_scored["Trust_Score"] = df_scored.apply(
        lambda r: compute_trust(int(r["rating_count"]), float(r["average_rating"])), axis=1
    )

    # 4. Compute final trust-aware score
    #    final_score = base_score × trust_multiplier  (single clean multiplier)
    df_scored["trust_final_score"] = (
        df_scored["base_score"] * df_scored["trust_multiplier"]
    )

    # 5. Normalise final score 0 → 1 within the current batch
    min_tf = df_scored["trust_final_score"].min()
    max_tf = df_scored["trust_final_score"].max()
    if max_tf == min_tf:
        df_scored["normalized_score"] = 1.0
    else:
        df_scored["normalized_score"] = (
            (df_scored["trust_final_score"] - min_tf) / (max_tf - min_tf)
        )

    # 6. Threshold-based filtering
    threshold = 0.5
    df_thresholded = df_scored[df_scored["normalized_score"] >= threshold].copy()

    if df_thresholded.empty:
        return "No suitable PG found based on your preferences. Try adjusting filters."

    # 7. Rank and rate
    df_ranked = rank_and_rate(df_thresholded, top_n)

    return df_ranked
