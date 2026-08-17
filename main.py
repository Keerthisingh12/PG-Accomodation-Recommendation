"""
main.py
────────
Entry point for the PG Accommodation Recommendation System (CLI version).

Usage:
    python main.py

Flow:
    1. Load raw dataset
    2. Preprocess (encode + scale + feature engineering)
    3. Collect user preferences via CLI prompts
    4. Run recommendation pipeline
    5. Display results as formatted cards with explanations
"""

import sys
from src.data_loader import load_raw_data, get_unique_locations
from src.preprocessor import preprocess, normalize_user_rent, normalize_user_meals
from src.recommender import recommend
from src.explainer import add_explanations
from config import DEFAULT_TOP_N


# ─────────────────────────────────────────────────────────────
# USER INPUT COLLECTION
# ─────────────────────────────────────────────────────────────

def collect_user_preferences(available_locations: list) -> dict:
    """Collect preferences from the user via the command line."""
    print("\n" + "═" * 55)
    print("   🏠  PG ACCOMMODATION RECOMMENDATION SYSTEM  🏠")
    print("═" * 55 + "\n")

    # ── Budget ───────────────────────────────────────────────
    while True:
        try:
            budget = float(input("💰  Enter your monthly budget (₹): ").strip())
            if budget <= 0:
                print("    ⚠️  Budget must be greater than 0. Try again.")
                continue
            break
        except ValueError:
            print("    ⚠️  Please enter a valid number.")

    # ── Gender ───────────────────────────────────────────────
    print("\n👤  Gender preference:")
    print("    0 = Boys Only  |  1 = Girls Only  |  2 = Any (Co-ed)")
    while True:
        try:
            gender = int(input("    Enter choice (0/1/2): ").strip())
            if gender not in (0, 1, 2):
                print("    ⚠️  Please enter 0, 1, or 2.")
                continue
            break
        except ValueError:
            print("    ⚠️  Please enter a valid number.")

    # ── Location ─────────────────────────────────────────────
    print(f"\n📍  Available locations: {', '.join(available_locations[:10])}{'...' if len(available_locations) > 10 else ''}")
    location = input("    Enter preferred location (or press Enter to skip): ").strip().lower()

    # ── Amenities ────────────────────────────────────────────
    print("\n🛠️   Amenity preferences (1 = Required, 0 = Not needed):")

    def ask_binary(label: str) -> int:
        while True:
            try:
                val = int(input(f"    {label}: ").strip())
                if val in (0, 1):
                    return val
                print("      ⚠️  Enter 0 or 1.")
            except ValueError:
                print("      ⚠️  Enter 0 or 1.")

    wifi    = ask_binary("WiFi required?        (1/0)")
    ac      = ask_binary("AC required?          (1/0)")
    laundry = ask_binary("Laundry required?     (1/0)")
    food    = ask_binary("Weekend food?         (1/0)")

    # ── Meals ────────────────────────────────────────────────
    print("\n🍽️   Meals per day:")
    while True:
        try:
            meals = int(input("    Enter 2 or 3: ").strip())
            if meals in (2, 3):
                break
            print("    ⚠️  Please enter 2 or 3.")
        except ValueError:
            print("    ⚠️  Please enter a valid number.")

    return {
        "budget":  budget,
        "gender":  gender,
        "location": location,
        "wifi":    wifi,
        "ac":      ac,
        "laundry": laundry,
        "food":    food,
        "meals":   meals,
    }


# ─────────────────────────────────────────────────────────────
# FEATURE VECTOR BUILDER
# ─────────────────────────────────────────────────────────────

def build_feature_vector(user_raw: dict, df) -> dict:
    """
    Convert raw user inputs to normalized feature values for scoring.

    IMPORTANT:
      - Rent and Meals_Per_Day are scaled using the same MinMaxScaler
        formula that was applied to the dataset during preprocessing.
      - Binary features (WiFi, AC, etc.) are already 0/1, no scaling needed.
    """
    return {
        "Rent":          normalize_user_rent(user_raw["budget"], df["Original_Rent"]),
        "WiFi":          user_raw["wifi"],
        "AC":            user_raw["ac"],
        "Laundry":       user_raw["laundry"],
        "Weekend_Food":  user_raw["food"],
        "Meals_Per_Day": normalize_user_meals(user_raw["meals"]),
        "Security":      0,       # not asked but included in weights; neutral = 0
        "Housekeeping":  0,
        "Power_Backup":  0,
    }


# ─────────────────────────────────────────────────────────────
# DISPLAY
# ─────────────────────────────────────────────────────────────

def display_results(results: "pd.DataFrame", user_raw: dict) -> None:
    """Print recommendation cards to the console."""
    results_with_explain = add_explanations(results, user_raw)

    gender_label = {0: "Boys", 1: "Girls", 2: "Co-ed"}.get(user_raw["gender"], "Any")

    print(f"\n{'═' * 55}")
    print(f"  🏆  TOP {len(results_with_explain)} PGs FOR YOU")
    print(f"  Budget: ₹{user_raw['budget']:,.0f}  |  Gender: {gender_label}")
    print(f"  Location: {user_raw['location'].title() or 'Any'}")
    print(f"{'═' * 55}\n")

    for _, row in results_with_explain.iterrows():
        if int(row["Rank"]) == 1:
             print("🔥 BEST MATCH 🔥\n")
        badge = f"[{row['Badge']}]" if row["Badge"] else ""

        meals_raw = int(round(row["Meals_Per_Day"] + 2))

        curfew_map = {0: "9:00 PM", 1: "10:00 PM", 2: "11:00 PM", 3: "No Curfew"}
        curfew_str = curfew_map.get(int(row.get("Curfew_Time", 2)), "—")

        # Clean amenity list
        amenities = []
        if row.get("WiFi") == 1: amenities.append("WiFi")
        if row.get("AC") == 1: amenities.append("AC")
        if row.get("Laundry") == 1: amenities.append("Laundry")
        if row.get("Parking") == 1: amenities.append("Parking")

        amenity_str = ", ".join(amenities) if amenities else "Basic"

        print("─" * 60)
        print(f"🏠 Rank #{int(row['Rank'])}  |  ⭐ {row['match_rating']}/5  {badge}")
        print("─" * 60)

        print(f"📍 Location   : {str(row['Location']).title()}")
        print(f"💰 Rent       : ₹{int(row['Original_Rent']):,}/month")
        print(f"🛏 Sharing    : {row['Sharing']}-person room")
        print(f"🍽 Meals/day  : {meals_raw}")
        print(f"🌙 Curfew     : {curfew_str}")

        print(f"\n📦 Amenities  : {amenity_str}")

        print(f"\n📊 Score Info:")
        print(f"   Amenity Score : {row['amenity_score']:.0%}")
        print(f"   Available Soon: {'Yes' if row['available_soon'] else 'No'}")

        print(f"\n💡 Why Recommended:")
        print(f"   {row['Why_Matched']}")

        print("─" * 60 + "\n")
    print(f"  Showing top {len(results_with_explain)} of your best matches.\n")

   # ─────────────────────────────────────────────
    # EXPORT CLEAN REPORT
    # ─────────────────────────────────────────────
    import os
    import pandas as pd
    from datetime import datetime

    os.makedirs("output", exist_ok=True)

    # -------- USER INPUT --------
    user_summary = pd.DataFrame([{
        "Generated On": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "Budget (₹)": user_raw["budget"],
        "Preferred Location": user_raw["location"].title(),
        "WiFi Required": "Yes" if user_raw["wifi"] else "No",
        "AC Required": "Yes" if user_raw["ac"] else "No",
        "Laundry Required": "Yes" if user_raw["laundry"] else "No",
        "Food Required": "Yes" if user_raw["food"] else "No",
        "Meals/Day": user_raw["meals"],
        "Gender": {0: "Boys", 1: "Girls", 2: "Co-ed"}.get(user_raw["gender"])
    }])

    # -------- RECOMMENDATIONS --------
    export_df = results_with_explain.copy()

    export_df = export_df[[
        "Rank",
        "Location",
        "Original_Rent",
        "Sharing",
        "Meals_Per_Day",
        "match_rating",
        "Badge",
        "Why_Matched"
    ]]

    # Format nicely
    export_df["Location"] = export_df["Location"].str.title()
    export_df["Meals_Per_Day"] = (export_df["Meals_Per_Day"] + 2).round().astype(int)
    export_df["match_rating"] = export_df["match_rating"].astype(str) + " / 5"

    export_df.columns = [
        "Rank",
        "Location",
        "Rent (₹/month)",
        "Sharing Type",
        "Meals per Day",
        "Rating",
        "Badge",
        "Why Recommended"
    ]

    # -------- SAVE FILE --------
    file_path = "output/recommendations.csv"

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("USER INPUT\n")

    user_summary.to_csv(file_path, mode="a", index=False)

    with open(file_path, "a", encoding="utf-8") as f:
        f.write("\nRECOMMENDATIONS\n")

    export_df.to_csv(file_path, mode="a", index=False)

    print(f"📁 Report saved to: {file_path}\n")
    


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    # ── 1. Load data ─────────────────────────────────────────
    try:
        df_raw = load_raw_data()
    except (FileNotFoundError, ValueError) as e:
        print(f"\n❌  {e}")
        sys.exit(1)

    # ── 2. Preprocess ─────────────────────────────────────────
    df, scaler = preprocess(df_raw)

    # ── 3. Collect user preferences ──────────────────────────
    locations = get_unique_locations(df_raw)
    try:
        user_raw = collect_user_preferences(locations)
    except KeyboardInterrupt:
        print("\n\n👋  Exiting. Goodbye!")
        sys.exit(0)
    except ValueError:
        print("\n❌  Invalid input detected. Please run again and enter numbers where required.")
        sys.exit(1)

    # ── 4. Build normalized feature vector ───────────────────
    user_features = build_feature_vector(user_raw, df)

    # ── 5. Run recommendation ─────────────────────────────────
    print("\n⏳  Finding best PG matches for you...")
    try:
        results = recommend(
            df=df,
            user_input=user_features,
            user_location=user_raw["location"],
            budget=user_raw["budget"],
            gender=user_raw["gender"],
            top_n=DEFAULT_TOP_N,
        )
    except ValueError as e:
        print(f"\n❌  {e}")
        sys.exit(0)

    # ── 6. Display results ────────────────────────────────────
    display_results(results, user_raw)


if __name__ == "__main__":
    main()