import os
import sys
import pandas as pd
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    sys.exit(
        "Missing SUPABASE_URL / SUPABASE_KEY environment variables.\n"
        "Set them in your terminal: export SUPABASE_URL='...' and export SUPABASE_KEY='...'"
    )

client = create_client(SUPABASE_URL, SUPABASE_KEY)
CSV_PATH = "literature_reference_dataset.csv"

def main():
    df = pd.read_csv(CSV_PATH)
    df = df.where(pd.notnull(df), None)
    records = df.to_dict(orient="records")

    result = client.table("literature_reference").upsert(
        records, on_conflict="record_id"
    ).execute()

    print(f"✅ Upserted {len(records)} literature benchmark rows into Supabase.")

if __name__ == "__main__":
    main()
