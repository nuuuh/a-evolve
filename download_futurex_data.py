#!/usr/bin/env python3
"""Download FutureX datasets and save to data/futurex/ directory."""

import json
import pandas as pd
from pathlib import Path
from datasets import load_dataset

def download_futurex_datasets():
    """Download both FutureX datasets and save as JSON and Parquet files."""

    data_dir = Path("data/futurex")
    data_dir.mkdir(parents=True, exist_ok=True)

    # Download FutureX-Past (historical resolved predictions)
    print("Downloading FutureX-Past dataset...")
    try:
        past_dataset = load_dataset("futurex-ai/Futurex-Past", split="train")
        past_df = past_dataset.to_pandas()

        # Save as multiple formats
        past_df.to_json(data_dir / "futurex_past.json", orient="records", indent=2)
        past_df.to_parquet(data_dir / "futurex_past.parquet")

        print(f"✅ FutureX-Past: {len(past_df)} tasks saved")
        print(f"   Date range: {past_df['end_time'].min()} to {past_df['end_time'].max()}")
        print(f"   Difficulty levels: {sorted(past_df['level'].unique())}")

    except Exception as e:
        print(f"❌ Failed to download FutureX-Past: {e}")

    # Download FutureX-Online (live predictions)
    print("\nDownloading FutureX-Online dataset...")
    try:
        online_dataset = load_dataset("futurex-ai/Futurex-Online", split="train")
        online_df = online_dataset.to_pandas()

        # Save as multiple formats
        online_df.to_json(data_dir / "futurex_online.json", orient="records", indent=2)
        online_df.to_parquet(data_dir / "futurex_online.parquet")

        print(f"✅ FutureX-Online: {len(online_df)} tasks saved")
        print(f"   Date range: {online_df['end_time'].min()} to {online_df['end_time'].max()}")
        print(f"   Difficulty levels: {sorted(online_df['level'].unique())}")

    except Exception as e:
        print(f"❌ Failed to download FutureX-Online: {e}")

    # Create combined dataset info
    try:
        if 'past_df' in locals() and 'online_df' in locals():
            combined_info = {
                "datasets": {
                    "futurex_past": {
                        "description": "Historical resolved predictions",
                        "count": len(past_df),
                        "date_range": [past_df['end_time'].min(), past_df['end_time'].max()],
                        "difficulty_levels": sorted(past_df['level'].unique()),
                        "columns": list(past_df.columns)
                    },
                    "futurex_online": {
                        "description": "Live weekly predictions",
                        "count": len(online_df),
                        "date_range": [online_df['end_time'].min(), online_df['end_time'].max()],
                        "difficulty_levels": sorted(online_df['level'].unique()),
                        "columns": list(online_df.columns)
                    }
                },
                "total_tasks": len(past_df) + len(online_df),
                "download_timestamp": pd.Timestamp.now().isoformat()
            }

            with open(data_dir / "dataset_info.json", "w") as f:
                json.dump(combined_info, f, indent=2)

            print(f"\n📊 Combined dataset info saved")
            print(f"   Total tasks: {combined_info['total_tasks']}")

    except Exception as e:
        print(f"⚠️  Could not create combined info: {e}")

    print(f"\n✅ All FutureX data saved to {data_dir}/")

if __name__ == "__main__":
    download_futurex_datasets()