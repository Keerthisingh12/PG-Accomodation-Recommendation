"""
src/explainer.py
─────────────────
Responsible for:
  - Generating human-readable "Why this PG?" explanations
  - Assigning display badges (Budget Pick, Premium, Best Value, Available Now)
  - Adding explanation and badge columns to the results DataFrame
"""

import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import BUDGET_BADGE_MAX_RENT, PREMIUM_AMENITY_MIN


# ─────────────────────────────────────────────────────────────
# EXPLANATION GENERATOR
# ─────────────────────────────────────────────────────────────

def explain_match(pg_row: pd.Series, user_raw: dict) -> str:
    """
    Build a human-readable reason string explaining why this PG was recommended.

    Args:
        pg_row:   One row from the results DataFrame
        user_raw: Raw user preferences dict (budget, wifi, ac, laundry, food, meals)

    Returns:
        Pipe-separated string of matched reasons, e.g.:
        "✅ WiFi | ❄️ AC | 💰 Well within budget | ⭐ High amenity density"
    """
    reasons = []

    # Amenity matches (only highlight if user asked for it)
    if user_raw.get("wifi") == 1 and pg_row.get("WiFi") == 1:
        reasons.append("✅ WiFi")
    if user_raw.get("ac") == 1 and pg_row.get("AC") == 1:
        reasons.append("❄️ AC included")
    if user_raw.get("laundry") == 1 and pg_row.get("Laundry") == 1:
        reasons.append("🫧 Laundry")
    if user_raw.get("food") == 1 and pg_row.get("Weekend_Food") == 1:
        reasons.append("🍽️ Weekend food")

    # Security combo
    if pg_row.get("Security") == 1 and pg_row.get("CCTV") == 1:
        reasons.append("🔒 Secure (CCTV + Guard)")

    # Budget headroom
    rent   = pg_row.get("Original_Rent", 0)
    budget = user_raw.get("budget", float("inf"))
    if budget > 0:
        headroom = (budget - rent) / budget
        if headroom >= 0.15:
            reasons.append("💰 Well within budget")
        elif headroom >= 0:
            reasons.append("💸 Within budget")

    # Amenity density
    if pg_row.get("amenity_score", 0) >= PREMIUM_AMENITY_MIN:
        reasons.append("⭐ High amenity density")

    # Availability
    if pg_row.get("available_soon", 0) == 1:
        reasons.append("🔥 Move-in within 7 days")

    # No curfew bonus
    if pg_row.get("Curfew_Time") == 3:
        reasons.append("🌙 No curfew")

    return " | ".join(reasons) if reasons else "Good overall match"


# ─────────────────────────────────────────────────────────────
# BADGE ASSIGNER
# ─────────────────────────────────────────────────────────────

def assign_badge(pg_row: pd.Series, median_ptv: float) -> str:
    """
    Assign one display badge to a PG based on its characteristics.

    Priority order: Budget Pick → Premium → Best Value → Available Now → (none)

    Args:
        pg_row:     One row from the results DataFrame
        median_ptv: Median price-to-value ratio across all result PGs

    Returns:
        Badge string (emoji + label), or empty string if none applies.
    """
    rent = pg_row.get("Original_Rent", 0)
    amenity = pg_row.get("amenity_score", 0)
    ptv = pg_row.get("price_to_value", float("inf"))
    soon = pg_row.get("available_soon", 0)

    if rent < BUDGET_BADGE_MAX_RENT:
        return "🟢 Budget Pick"
    if amenity >= PREMIUM_AMENITY_MIN:
        return "⭐ Premium"
    if ptv < median_ptv:
        return "💡 Best Value"
    if soon == 1:
        return "🔥 Available Now"
    return ""


# ─────────────────────────────────────────────────────────────
# ATTACH TO RESULTS DATAFRAME
# ─────────────────────────────────────────────────────────────

def add_explanations(df: pd.DataFrame, user_raw: dict) -> pd.DataFrame:
    """
    Add 'Why_Matched' and 'Badge' columns to the results DataFrame.

    Args:
        df:       Ranked results DataFrame
        user_raw: Raw user preferences dict

    Returns:
        DataFrame with two new columns: Why_Matched, Badge
    """
    df = df.copy()

    # Use median price-to-value of the result set for badge threshold
    median_ptv = df["price_to_value"].median() if "price_to_value" in df.columns else 0.0

    df["Why_Matched"] = df.apply(
        lambda row: explain_match(row, user_raw), axis=1
    )
    df["Badge"] = df.apply(
        lambda row: assign_badge(row, median_ptv), axis=1
    )

    return df
