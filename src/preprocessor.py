"""
src/preprocessor.py
────────────────────
Responsible for:
  - Encoding categorical columns (binary Yes/No, Gender, Food_Type, etc.)
  - Preserving Original_Rent before scaling (needed for hard filtering)
  - Scaling numeric features with MinMaxScaler
  - Engineering derived features (amenity_score, price_to_value, etc.)
  - Providing helper to normalize user input using the same scale
"""

import os
import sys
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import BINARY_COLS, AMENITY_COLS, SCALE_COLS, AVAILABLE_SOON_DAYS

# ── Module-level scaler (fitted during preprocess(), reused for user input) ──
_scaler: MinMaxScaler = MinMaxScaler()
_scaler_fitted: bool = False


# ─────────────────────────────────────────────────────────────
# MAIN PREPROCESSING PIPELINE
# ─────────────────────────────────────────────────────────────

def preprocess(df: pd.DataFrame) -> tuple:
    """
    Full preprocessing pipeline for the raw PG dataset.

    Steps:
      1. Fill missing amenity values with 'No'
      2. Encode all Yes/No columns to 1/0
      3. Encode Gender, Food_Type, Curfew_Time, Availability
      4. Preserve Original_Rent before scaling
      5. Engineer derived features (amenity_score, price_to_value, etc.)
      6. Scale numeric columns: Rent, Meals_Per_Day, Floors

    Returns:
        Tuple of (processed_df, fitted_MinMaxScaler)
    """
    global _scaler, _scaler_fitted
    df = df.copy()

    # ── Step 1: Fill missing values ──────────────────────────
    amenity_defaults = {col: "No" for col in BINARY_COLS if col in df.columns}
    df = df.fillna(amenity_defaults)

    # ── Step 2: Encode Yes/No binary columns → 1 / 0 ────────
    for col in BINARY_COLS:
        if col in df.columns:
            df[col] = (
                df[col]
                .map({"Yes": 1, "No": 0})
                .fillna(0)
                .astype(int)
            )

    # ── Step 3: Encode categorical columns ───────────────────
    df["Gender"] = df["Gender"].map({"Boys": 0, "Girls": 1, "Co-ed": 2})

    df["Food_Type"] = df["Food_Type"].map({"Veg": 0, "Non-Veg": 1, "Both": 2})

    df["Curfew_Time"] = df["Curfew_Time"].map({
        "9:00 PM":   0,
        "10:00 PM":  1,
        "11:00 PM":  2,
        "No Curfew": 3,
    })

    df["Availability"] = df["Availability"].map({"Available": 1, "Full": 0})

    df["Available_From"] = pd.to_datetime(
    df["Available_From"],
    format="%Y-%m-%d",   
    errors="coerce"
)

    # ── Step 4: Preserve raw rent BEFORE scaling ─────────────
    #   BUG FIX: original code compared SCALED rent with manually
    #   re-normalized budget — they used different formulas.
    #   Now we always filter on Original_Rent (raw ₹ vs raw ₹).
    df["Original_Rent"] = df["Rent"].copy()

    # ── Step 5: Normalise location ───────────────────────────
    df["Location"] = df["Location"].str.lower().str.strip()

    # ── Step 6: Feature engineering ──────────────────────────
    df = _engineer_features(df)

    # ── Step 7: Scale numeric features ───────────────────────
    df[SCALE_COLS] = _scaler.fit_transform(df[SCALE_COLS])
    _scaler_fitted = True

    return df, _scaler


# ─────────────────────────────────────────────────────────────
# FEATURE ENGINEERING
# ─────────────────────────────────────────────────────────────

def _engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived columns that improve recommendation quality."""

    # 1. Amenity Density Score — fraction of available amenities (0 to 1)
    amenity_present = [c for c in AMENITY_COLS if c in df.columns]
    df["amenity_score"] = (
        df[amenity_present].sum(axis=1) / len(amenity_present)
    )

    # 2. Price-to-Value Ratio — lower means better value for money
    df["price_to_value"] = df["Rent"] / (df["amenity_score"] + 0.01)

    # 3. Curfew Flexibility (0 = strictest, 1 = no curfew at all)
    df["curfew_score"] = df["Curfew_Time"] / 3.0

    # 4. Available Soon Flag — moves in within AVAILABLE_SOON_DAYS days
    today = pd.Timestamp.today().normalize()
    df["days_until_available"] = (
        (df["Available_From"] - today)
        .dt.days
        .clip(lower=0)
        .fillna(999)
    )
    df["available_soon"] = (
        df["days_until_available"] <= AVAILABLE_SOON_DAYS
    ).astype(int)

    return df


# ─────────────────────────────────────────────────────────────
# USER INPUT NORMALIZATION HELPERS
# ─────────────────────────────────────────────────────────────

def normalize_user_rent(budget: float, original_rent_series: pd.Series) -> float:
    """
    Normalize a raw budget (₹) using the same min/max as the dataset.
    This ensures user budget is on the same scale [0,1] as df["Rent"].
    """
    min_r = original_rent_series.min()
    max_r = original_rent_series.max()
    return float((budget - min_r) / (max_r - min_r + 1e-9))


def normalize_user_meals(meals: int) -> float:
    """
    Normalize user's meals preference (2 or 3) to [0, 1].
    MinMaxScaler on [2, 3] maps: 2 → 0.0, 3 → 1.0
    Formula: (x - 2) / (3 - 2) = x - 2
    """
    return float(max(0.0, min(1.0, (meals - 2) / 1.0)))
