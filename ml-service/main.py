"""
ml-service/main.py
──────────────────
FastAPI ML Microservice wrapping the existing src/ recommendation pipeline.

Endpoints:
  POST /recommend          — full recommendation pipeline
  POST /analyze-sentiment  — HuggingFace sentiment analysis
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

from src.data_loader import load_raw_data
from src.preprocessor import preprocess, normalize_user_meals
from src.recommender import recommend
from src.explainer import add_explanations
from src.sentiment_analyzer import analyze as analyze_sentiment, sentiment_label

app = FastAPI(title="PG Recommendation ML Service")

# ── Load & preprocess dataset once at startup ──
df = None


@app.on_event("startup")
async def startup():
    global df
    raw = load_raw_data()
    df, _ = preprocess(raw)
    print(f"✅ ML Service: loaded {len(df)} preprocessed PG records")


# ── Request schemas ──

class RecommendRequest(BaseModel):
    user_preferences: dict
    db_stats: Optional[dict] = None


class AnalyzeSentimentRequest(BaseModel):
    review_text: str


# ── Routes ──

@app.post("/recommend")
async def recommend_endpoint(req: RecommendRequest):
    """Run the full recommendation pipeline with external db_stats."""
    user = req.user_preferences

    # Normalize user input
    user_normalized = {"Meals_Per_Day": normalize_user_meals(user.get("meals", 2))}
    if user.get("wifi"):
        user_normalized["WiFi"] = 1
    if user.get("ac"):
        user_normalized["AC"] = 1
    if user.get("laundry"):
        user_normalized["Laundry"] = 1
    if user.get("food"):
        user_normalized["Weekend_Food"] = 1

    # Parse db_stats
    db_stats_in = None
    review_stats_in = None
    if req.db_stats:
        db_stats_in = req.db_stats.get("ratings")
        review_stats_in = req.db_stats.get("reviews")

    result = recommend(
        df,
        user_normalized,
        user.get("location", "").strip().lower(),
        float(user.get("budget", 15000)),
        int(user.get("gender", 2)),
        sharing=user.get("sharing", "Any"),
        db_stats=db_stats_in,
        review_stats=review_stats_in,
    )

    if isinstance(result, str):
        return {"error": result, "results": []}

    # Attach explanations and badges
    result = add_explanations(result, user)

    records = result.to_dict(orient="records")
    # Convert numpy types to native Python for JSON serialization
    cleaned = _clean_records(records)
    return {"results": cleaned, "error": None}


@app.post("/analyze-sentiment")
async def analyze_sentiment_endpoint(req: AnalyzeSentimentRequest):
    """Analyze review text and return sentiment score."""
    score = analyze_sentiment(req.review_text)
    return {
        "sentiment_score": score,
        "sentiment_label": sentiment_label(score),
    }


# ── Helpers ──

def _clean_records(records: list) -> list:
    """Convert numpy types to native Python for JSON serialization."""
    import math
    cleaned = []
    for rec in records:
        clean = {}
        for k, v in rec.items():
            if isinstance(v, (float,)):
                if math.isnan(v) or math.isinf(v):
                    clean[k] = None
                else:
                    clean[k] = round(float(v), 4)
            elif isinstance(v, (int,)):
                clean[k] = int(v)
            elif isinstance(v, dict):
                clean[k] = v
            else:
                clean[k] = v
        cleaned.append(clean)
    return cleaned
