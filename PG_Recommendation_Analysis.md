# 🏠 PG Accommodation Recommendation System — Full Analysis & Improvement Plan

---

## 🔍 1. Problems in the Current System

Based on direct inspection of `main.py` and `PG_Full_Feature_Dataset_v2.csv`:

### Critical Issues

| # | Problem | Location in Code |
|---|---------|-----------------|
| 1 | **Flat monolithic file** — all logic (load, clean, encode, score, UI) crammed into one 194-line file | `main.py` (entire file) |
| 2 | **Broken hard filter** — `df["Rent"] <= user_budget` compares *scaled* rent to *scaled* budget, but `user_budget` is re-computed manually while `df["Rent"]` was scaled by `scaler.fit_transform`. These will rarely be exactly comparable scale-for-scale | Lines 102–122 |
| 3 | **Location match is all-or-nothing** — location bonus is only `-0.2` for exact match; a typo or partial match ("hennur" vs "hennur road") gives **zero** bonus | Lines 147–148 |
| 4 | **Gender filter is too strict** — Co-ed PGs (value 2) should be valid for both Boys (0) and Girls (1), but current filter only does exact equality | Line 122 |
| 5 | **Score includes unused key `Gender`** in `user_input` dict but weights dict doesn't — causing silent data drift | Lines 106, 133 |
| 6 | **`Meals_Per_Day` weight is wrong** — user enters raw `2` or `3`, but PGs are already **scaled** (0.0–1.0) after `fit_transform`. The comparison `abs(scaled_pg_val - raw_user_val/3)` is arithmetically inconsistent | Lines 75–76, 113, 144 |
| 7 | **No error handling** — empty `df_filtered` crashes silently with a confusing pandas error | Line 172 |
| 8 | **Weights are hardcoded** — user cannot express priority (e.g., "WiFi is most important to me") | Lines 133–140 |
| 9 | **Dropped features unused in scoring** — Security, CCTV, Power_Backup, Housekeeping, Parking, Lift, Drinking_Water, Curfew_Time, Food_Type are encoded but never scored | — |
| 10 | **No explanation output** — user has no idea *why* a PG was recommended | Lines 177–194 |

---

## ✅ 2. Improved Architecture

### Recommended Folder Structure

```
PG_Recommendation/
├── data/
│   ├── raw/
│   │   └── PG_Full_Feature_Dataset_v2.csv
│   └── processed/
│       └── pg_encoded.pkl            ← cached encoded dataframe
│
├── src/
│   ├── __init__.py
│   ├── data_loader.py                ← load & validate CSV
│   ├── preprocessor.py               ← encode, scale, feature engineering
│   ├── recommender.py                ← core scoring & ranking logic
│   ├── explainer.py                  ← "Why this PG?" explanation generator
│   └── utils.py                      ← helpers (fuzzy match, badge logic)
│
├── api/
│   ├── app.py                        ← Flask REST API
│   └── routes/
│       ├── recommend.py              ← POST /recommend
│       └── pg_detail.py              ← GET /pg/<id>
│
├── ui/
│   ├── index.html
│   ├── style.css
│   └── app.js
│
├── tests/
│   ├── test_recommender.py
│   └── test_preprocessor.py
│
├── config.py                         ← weights, thresholds, paths
├── requirements.txt
└── README.md
```

### Module Responsibilities

```
data_loader.py   → loads CSV, validates columns, returns raw df
preprocessor.py  → encoding + scaling + feature engineering
recommender.py   → hard filter → scoring → ranking → output
explainer.py     → generates human-readable reason strings
api/app.py       → Flask wrapper around recommender
ui/              → optional HTML/JS frontend
```

---

## 🧠 3. Enhanced Algorithm (with Formulas)

### 3a. Fix the Hard Filter

```python
# CURRENT (broken) — compares scaled rent to manually re-scaled budget
df_filtered = df[df["Rent"] <= user_budget]

# CORRECT — filter on ORIGINAL rent before any scaling
df_filtered = df[
    (df["Original_Rent"] <= user_budget_raw) &   # raw ₹ vs raw ₹
    (df["Availability"] == 1) &
    (df["Gender"].isin(valid_genders))            # see gender fix below
]
```

### 3b. Fix Gender Filtering

```python
# Map what genders are acceptable for user
gender_map = {
    "Boys":   [0, 2],   # Boys or Co-ed
    "Girls":  [1, 2],   # Girls or Co-ed
    "Co-ed":  [0, 1, 2] # any
}
valid_genders = gender_map[user_gender_str]
df_filtered = df[df["Gender"].isin(valid_genders)]
```

### 3c. Better Scoring Formula

Replace the simple absolute-difference sum with a **Weighted Euclidean Distance** on normalized features:

```
score(PG) = √ Σ [ w_i × (pg_i − user_i)² ]
```

Where:
- `pg_i` and `user_i` are both **MinMax normalized** [0, 1]
- `w_i` is the weight for feature `i`
- Lower score = better match

**In code:**

```python
score = 0.0
for feature, weight in weights.items():
    diff = df_copy[feature] - user_input_normalized[feature]
    score += weight * (diff ** 2)
df_copy["score"] = np.sqrt(score)
```

### 3d. Dynamic Weights (User-Priority Based)

Let users rank their top priorities. Redistribute weights accordingly:

```python
# User selects: "My top priority is WiFi, second is AC"
PRIORITY_BOOSTS = {
    "budget":    0.40,
    "wifi":      0.20,
    "ac":        0.10,
    "laundry":   0.10,
    "food":      0.10,
    "meals":     0.10,
}

def adjust_weights(user_priorities: list[str]) -> dict:
    """
    user_priorities = ["wifi", "ac"]  → boost those two by redistributing
    """
    base = PRIORITY_BOOSTS.copy()
    boost_amount = 0.05
    for p in user_priorities[:2]:   # top 2 priorities only
        if p in base:
            base[p] += boost_amount
            # reduce from lowest-priority feature
            min_key = min(base, key=base.get)
            base[min_key] = max(0.0, base[min_key] - boost_amount)
    return base
```

### 3e. Fuzzy Location Matching

Replace exact string match with fuzzy ratio:

```python
# pip install rapidfuzz  (lightweight, no dependency hell)
from rapidfuzz import fuzz

def location_score(pg_location: str, user_location: str) -> float:
    ratio = fuzz.partial_ratio(pg_location, user_location) / 100.0
    return ratio   # 0.0 to 1.0

# In scoring loop:
df_copy["location_score"] = df_copy["Location"].apply(
    lambda loc: location_score(loc, user_location)
)
# Higher location_score = better → subtract from distance score
df_copy["final_score"] = df_copy["score"] - (LOCATION_WEIGHT * df_copy["location_score"])
```

### 3f. Rating Conversion

```python
# Correct normalization → rating
min_s = df_copy["final_score"].min()
max_s = df_copy["final_score"].max()
df_copy["normalized"] = (df_copy["final_score"] - min_s) / (max_s - min_s + 1e-9)
df_copy["match_rating"] = ((1 - df_copy["normalized"]) * 4 + 1).round(1)
# Rating is now always in [1.0, 5.0] — never 0
```

### 3g. Summary of All Fixes

| Issue | Fix |
|-------|-----|
| Rent comparison mismatch | Filter on `Original_Rent` before scaling |
| Gender too strict | Use `isin([allowed_genders])` |
| Location all-or-nothing | rapidfuzz partial ratio |
| Meals scale mismatch | Scale user input using same scaler |
| Missing features in score | Add Security, CCTV, Housekeeping to weights |
| No empty-result guard | Check `len(df_filtered) == 0` and raise friendly error |
| Rating can be 0 | Clamp rating to [1, 5] range |

---

## ✨ 4. New Features to Add

### 4a. Feature Engineering (add to `preprocessor.py`)

```python
# 1. Amenity Density Score (count of available amenities / total)
amenity_cols = ["WiFi","AC","Laundry","Parking","Housekeeping",
                "Lift","Security","CCTV","Power_Backup","Drinking_Water"]
df["amenity_score"] = df[amenity_cols].sum(axis=1) / len(amenity_cols)

# 2. Price-to-Value Ratio (lower = better value)
df["price_to_value"] = df["Rent"] / (df["amenity_score"] + 0.01)

# 3. Popularity Score (placeholder — set uniform until you have real click data)
df["popularity_score"] = 0.5

# 4. Curfew Flexibility Score
df["curfew_score"] = df["Curfew_Time"] / 3.0   # 0 = strictest, 1 = no curfew

# 5. Available Soon Flag
today = pd.Timestamp.today()
df["days_until_available"] = (df["Available_From"] - today).dt.days.clip(lower=0)
df["available_soon"] = (df["days_until_available"] <= 7).astype(int)
```

### 4b. Recommendation Explanation (`explainer.py`)

```python
def explain(pg_row, user_input) -> str:
    reasons = []
    if pg_row["WiFi"] == 1 and user_input["wifi"] == 1:
        reasons.append("✅ WiFi available")
    if pg_row["Original_Rent"] <= user_input["budget"] * 0.85:
        reasons.append("💰 Well within your budget")
    if pg_row["AC"] == 1 and user_input["ac"] == 1:
        reasons.append("❄️ AC included")
    if pg_row["amenity_score"] > 0.7:
        reasons.append("⭐ High amenity density")
    if pg_row["available_soon"]:
        reasons.append("🗓️ Available within 7 days")
    return " | ".join(reasons) if reasons else "Good overall match"
```

### 4c. Badges

```python
def assign_badge(pg_row) -> str:
    if pg_row["Original_Rent"] < 8000:            return "🟢 Budget Pick"
    if pg_row["amenity_score"] > 0.75:            return "⭐ Premium"
    if pg_row["price_to_value"] < median_ptv:     return "💡 Best Value"
    if pg_row["available_soon"]:                  return "🔥 Available Now"
    return ""
```

---

## 🎨 5. UI/UX Suggestions

### Recommended: Flask API + Single-Page HTML/JS UI

No React needed. A clean HTML/JS page calling a Flask endpoint is **faster to build, easier to deploy, and sufficient** for this use case.

**Form fields to show:**
- Budget slider (₹5,000 – ₹30,000) with live value label
- Amenity checkboxes (WiFi, AC, Laundry, etc.)
- Gender radio buttons (Boys / Girls / Any)
- Location text field with autocomplete from known locations
- Priority ranking drag-list ("What matters most to you?")
- Number of results selector (5 / 10 / 20)

**Result cards should show:**

```
┌──────────────────────────────────────────────┐
│  PG101 · Hennur               ⭐ 4.7   [Premium] │
│  ₹17,868/mo · Single sharing                   │
│  ✅ WiFi  ❄️ AC  🫧 Laundry  🔒 Security       │
│  🍽️ 2 meals/day  |  Curfew: 11:00 PM           │
│  Why matched: ✅ WiFi | 💰 Within budget        │
│                         [View Details] [Save]  │
└──────────────────────────────────────────────┘
```

**Additional UI features:**
- Sort by: Rating / Rent (low-high) / Amenities
- Filter chips: "WiFi Only", "No Curfew", "Available Now"
- Compare mode: checkbox 2 PGs → side-by-side diff table
- Dark mode toggle

---

## ⚡ 6. Performance & Scalability

### Phase 1 — CSV (current, <1000 rows)
- Pre-encode CSV at startup and cache as `.pkl` (saves ~80ms per request)
- Caching pattern:
```python
import pickle, os
CACHE = "data/processed/pg_encoded.pkl"
if os.path.exists(CACHE):
    df = pickle.load(open(CACHE, "rb"))
else:
    df = preprocess(load_csv())
    pickle.dump(df, open(CACHE, "wb"))
```

### Phase 2 — REST API with Flask

```python
# api/app.py
from flask import Flask, request, jsonify
from src.recommender import recommend_pg

app = Flask(__name__)

@app.route("/recommend", methods=["POST"])
def recommend():
    user_input = request.json          # {budget, wifi, ac, gender, location, ...}
    results = recommend_pg(user_input, top_n=10)
    return jsonify(results.to_dict(orient="records"))

@app.route("/locations", methods=["GET"])
def locations():
    return jsonify(df["Location"].str.title().unique().tolist())
```

**Endpoint design:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/recommend` | Get top-N PGs for user input |
| GET | `/pg/<id>` | Full details of one PG |
| GET | `/locations` | List all available locations |
| GET | `/stats` | Aggregate stats (avg rent, etc.) |

### Phase 3 — Database Migration (CSV → PostgreSQL)

```
CSV columns → PostgreSQL table: pgs
  - Primary key: pg_id (VARCHAR)
  - Index on: location, rent, gender, availability
  - JSONB column for amenities (flexible future expansion)
```

Query pattern for filtering:
```sql
SELECT * FROM pgs
WHERE availability = true
  AND rent <= 15000
  AND gender IN ('Co-ed', 'Boys')
ORDER BY rent ASC;
```

### Phase 4 — Real-time Handling

- Add Redis cache for repeated queries (same location + budget)
- Cache TTL: 5 minutes (data doesn't update that fast)
- Use connection pooling (SQLAlchemy) if on PostgreSQL

---

## 🚀 7. Future Roadmap

```
v1.0 (NOW)          Fix bugs + modularize code + add explanation output
v1.1 (Week 2)       Add Flask API + HTML/JS UI with cards
v1.2 (Week 3)       Add amenity_score, price_to_value, badge system
v1.3 (Week 4)       Fuzzy location, dynamic weights, explainer
v2.0 (Month 2)      Migrate to PostgreSQL + deploy on Railway/Render
v2.1 (Month 2)      Add user accounts + saved searches
v3.0 (Future)       KNN recommendation (once you collect user interaction data)
v3.1 (Future)       Clustering PGs into tiers (Budget / Mid / Premium)
v3.2 (Future)       Hybrid system: collaborative + content-based filtering
```

### Optional ML Extensions (Lightweight)

| Technique | Library | When to add |
|-----------|---------|-------------|
| KNN-based recommendation | `scikit-learn` KNeighborsClassifier | When you have > 500 user sessions |
| KMeans clustering of PGs | `scikit-learn` KMeans | To auto-group into Budget/Premium tiers |
| TF-IDF for NLP input | `scikit-learn` TfidfVectorizer | For "cheap PG with WiFi near metro" input |
| Hybrid filtering | Custom weighted blend | When collaborative data exists |

### NLP Input Example (Lightweight TF-IDF approach)

```python
# "I need a cheap PG with WiFi and AC in Hennur"
# → parse keywords → map to features → run recommender

keyword_map = {
    "cheap": {"budget": 8000},
    "wifi":  {"wifi": 1},
    "ac":    {"ac": 1},
    "laundry": {"laundry": 1},
    "no curfew": {"curfew_preference": 3},
}

def parse_natural_input(text: str) -> dict:
    user_prefs = {}
    text_lower = text.lower()
    for keyword, mapping in keyword_map.items():
        if keyword in text_lower:
            user_prefs.update(mapping)
    # extract location using simple regex
    location_match = re.search(r"in ([a-z ]+)", text_lower)
    if location_match:
        user_prefs["location"] = location_match.group(1).strip()
    return user_prefs
```

---

## 📋 Immediate Action Items (Priority Order)

1. **[P0 Bug]** Fix the rent filter — use `Original_Rent` for hard filtering
2. **[P0 Bug]** Fix gender filter to allow Co-ed for all genders
3. **[P0 Bug]** Fix Meals_Per_Day scale — apply same scaler to user input
4. **[P1]** Add `len(df_filtered) == 0` guard with friendly error message
5. **[P1]** Refactor into `src/` modules (data_loader, preprocessor, recommender)
6. **[P2]** Add `amenity_score` and `price_to_value` features
7. **[P2]** Add `explain()` function and show reasons in output
8. **[P2]** Add rapidfuzz for location matching
9. **[P3]** Build Flask API with `/recommend` endpoint
10. **[P3]** Build HTML/JS card-based UI
