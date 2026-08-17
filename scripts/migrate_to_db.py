import os
import sys
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DATA_RAW_PATH, DATABASE_URL

def migrate():
    # 1. Ensure the database exists
    engine = create_engine(DATABASE_URL)
    if not database_exists(engine.url):
        create_database(engine.url)
        print(f"Created database: {engine.url.database}")
    else:
        print(f"Database {engine.url.database} already exists.")

    # 2. Migrate PG Dataset.csv
    if os.path.exists(DATA_RAW_PATH):
        print(f"Migrating {DATA_RAW_PATH} to 'pg_dataset' table...")
        df_main = pd.read_csv(DATA_RAW_PATH)
        df_main.to_sql("pg_dataset", engine, if_exists="replace", index=False)
        print(f"Inserted {len(df_main)} rows into 'pg_dataset'.")
    else:
        print(f"WARNING: {DATA_RAW_PATH} not found.")

    # 3. Migrate ratings.csv
    ratings_path = os.path.join(os.path.dirname(DATA_RAW_PATH), "..", "ratings.csv")
    if os.path.exists(ratings_path):
        print(f"Migrating {ratings_path} to 'ratings' table...")
        df_ratings = pd.read_csv(ratings_path)
        df_ratings.to_sql("ratings", engine, if_exists="replace", index=False)
        print(f"Inserted {len(df_ratings)} rows into 'ratings'.")
    else:
        print(f"No ratings.csv found at {ratings_path}. Skipping.")

    # 4. Migrate reviews.csv
    reviews_path = os.path.join(os.path.dirname(DATA_RAW_PATH), "..", "reviews.csv")
    if os.path.exists(reviews_path):
        print(f"Migrating {reviews_path} to 'reviews' table...")
        df_reviews = pd.read_csv(reviews_path)
        df_reviews.to_sql("reviews", engine, if_exists="replace", index=False)
        print(f"Inserted {len(df_reviews)} rows into 'reviews'.")
    else:
        print(f"No reviews.csv found at {reviews_path}. Skipping.")

    print("Migration complete!")

if __name__ == "__main__":
    migrate()
