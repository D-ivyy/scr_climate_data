"""
extract_solar_pv.py
-------------------
Reads solar_pv_1.json and extracts the 'id' and 'asset_name' fields
from every item, writing them to solar_pv_assets.csv.
"""

import json
import csv
import os

INPUT_FILE = os.path.join(os.path.dirname(__file__), "solar_pv_4.json")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "solar_pv_assets_4.csv")


def main():
    print(f"Reading {INPUT_FILE} ...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", [])
    total = len(items)
    print(f"Found {total} assets.")

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["id", "asset_name"])          # header row
        for item in items:
            writer.writerow([item["id"], item["asset_name"]])

    print(f"Done! CSV written to: {OUTPUT_FILE}")
    print(f"  Rows written: {total}")


if __name__ == "__main__":
    main()
