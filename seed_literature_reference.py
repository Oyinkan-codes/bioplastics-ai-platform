import os
import sys
import pandas as pd
import numpy as np
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    sys.exit(
        "Missing SUPABASE_URL / SUPABASE_KEY environment variables.\n"
        "Set them in your terminal before running this script."
    )

client = create_client(SUPABASE_URL, SUPABASE_KEY)
CSV_PATH = "literature_reference_dataset.csv"

# Columns defined as NUMERIC in schema.sql
NUMERIC_COLS = [
    "filler_loading_wt_pct",
    "measured_value",
    "value_range_low",
    "value_range_high",
    "elongation_pct",
]

def clean_record(row):
    """Ensure numeric values are parsed correctly and required fields have non-null fallbacks."""
    record = {}
    for col, val in row.items():
        if col in NUMERIC_COLS:
            try:
                parsed_val = float(val)
                record[col] = None if np.isnan(parsed_val) else parsed_val
            except (ValueError, TypeError):
                record[col] = None
        else:
            if isinstance(val, float) and np.isnan(val):
                record[col] = None
            else:
                record[col] = str(val) if val is not None else None

    # Handle NOT NULL constraint on citation_url
    if not record.get("citation_url"):
        record["citation_url"] = "https://biomatx.ai/benchmarks"

    return record

def main():
    if not os.path.exists(CSV_PATH):
        sys.exit(f"Error: {CSV_PATH} not found in current directory.")

    df = pd.read_csv(CSV_PATH)
    raw_records = df.to_dict(orient="records")
    clean_records = [clean_record(r) for r in raw_records]

    result = client.table("literature_reference").upsert(
        clean_records, on_conflict="record_id"
    ).execute()

    print(f"✅ Successfully upserted {len(clean_records)} literature benchmark rows into Supabase!")

if __name__ == "__main__":
    main()
