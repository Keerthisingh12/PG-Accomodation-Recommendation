import os

# ─────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────
BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
DATA_RAW_PATH   = os.path.join(BASE_DIR, "data", "raw", "PG Dataset.csv")
DATA_CACHE_PATH = os.path.join(BASE_DIR, "data", "processed", "pg_encoded.pkl")
DATABASE_URL    = os.environ.get("DATABASE_URL", "postgresql://localhost/pg_recommendation")

# ─────────────────────────────────────────────
# COLUMN DEFINITIONS
# ─────────────────────────────────────────────
BINARY_COLS = [
    "WiFi", "AC", "Laundry", "Parking", "Housekeeping", "Lift",
    "Security", "CCTV", "Power_Backup", "Drinking_Water",
    "Pets_Allowed", "Visitors_Allowed", "Smoking_Area", "Weekend_Food"
]

AMENITY_COLS = [
    "WiFi", "AC", "Laundry", "Parking", "Housekeeping",
    "Lift", "Security", "CCTV", "Power_Backup", "Drinking_Water"
]

SCALE_COLS = ["Rent", "Meals_Per_Day", "Floors"]

REQUIRED_COLUMNS = [
    "PG_ID", "Location", "Rent", "Sharing", "Gender",
    "Meals_Per_Day", "Weekend_Food", "WiFi", "AC", "Laundry",
    "Parking", "Housekeeping", "Lift", "Security", "CCTV",
    "Power_Backup", "Drinking_Water", "Floors", "Food_Type",
    "Pets_Allowed", "Visitors_Allowed", "Smoking_Area",
    "Curfew_Time", "Available_From", "Availability"
]

# ─────────────────────────────────────────────
# SCORING WEIGHTS  (must sum to 1.0)
# ─────────────────────────────────────────────
# NOTE: Rent is intentionally excluded from scoring.
# Budget is already enforced as a hard ceiling in hard_filter().
# Including Rent here would penalize cheaper PGs, producing nonsensical
# results where a ₹6,000 PG scores lower than a ₹10,400 PG for a ₹10,500 budget.
DEFAULT_WEIGHTS = {
    # Rent removed — budget is a ceiling, not a scoring target
    "WiFi":          0.20,
    "AC":            0.15,
    "Laundry":       0.12,
    "Weekend_Food":  0.08,
    "Meals_Per_Day": 0.12,
    "Security":      0.10,
    "Housekeeping":  0.08,
    "Power_Backup":  0.08,
    "Distance_From_Center_KM": 0.07,
}

# ─────────────────────────────────────────────
# LOCATION MATCHING
# ─────────────────────────────────────────────
LOCATION_WEIGHT           = 0.25   # how much location match reduces final score
LOCATION_FUZZY_THRESHOLD  = 60     # minimum fuzzy ratio (0-100) to count as match

# ─────────────────────────────────────────────
# BADGE THRESHOLDS
# ─────────────────────────────────────────────
BUDGET_BADGE_MAX_RENT     = 9000   # ₹ — below this → "Budget Pick"
PREMIUM_AMENITY_MIN       = 0.70   # amenity_score ≥ this → "Premium"
AVAILABLE_SOON_DAYS       = 7      # days_until_available ≤ this → "Available Now"

# ─────────────────────────────────────────────
# GENDER COMPATIBILITY MAP
# ─────────────────────────────────────────────
# { user_gender_code : [acceptable_pg_gender_codes] }
GENDER_COMPAT = {
    0: [0, 2],      # Boys → Boys PG or Co-ed PG
    1: [1, 2],      # Girls → Girls PG or Co-ed PG
    2: [0, 1, 2],   # Co-ed preferred → any PG
}

# ─────────────────────────────────────────────
# RECOMMENDATION
# ─────────────────────────────────────────────
DEFAULT_TOP_N = 5
