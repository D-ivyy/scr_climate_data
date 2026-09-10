"""
download_physical_risks.py
--------------------------
Reads solar_pv_assets.csv and downloads the physical_risks Excel export
for every asset ID, saving each file as:
    physical_risks_exports/<asset_name>_physical_risks.xlsx

Usage:
    python3 download_physical_risks.py                    # full run
    python3 download_physical_risks.py --token <JWT>      # fresh token
    python3 download_physical_risks.py --start-from 500   # resume from row 500
    python3 download_physical_risks.py --retry-failed     # retry only failed_assets.csv
    python3 download_physical_risks.py --limit 5          # test with 5 assets
"""

import csv
import os
import sys
import time
import argparse
import requests
from pathlib import Path

# ── Configuration ──────────────────────────────────────────────────────────────
DEFAULT_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJzdWIiOiIyMCIsImlhdCI6MTc4NjcxNjE2MSwic3RhdHVzIjoiQ1JFQVRFRCIsImV4cCI6MTc4Njc1OTM2MX0"
    ".fvptz61buw-sph_7LyyAEa8IkcGslJYzIpjH_7nTNbM"
)

BASE_URL    = "https://api.scientificratings.com/climate-metrics-service/api/exports/assets/{id}/physical_risks"
CSV_FILE    = Path(__file__).parent / "solar_pv_assets_4.csv"
OUTPUT_DIR  = Path(__file__).parent / "physical_risks_exports_3"
FAILED_LOG  = Path(__file__).parent / "failed_assets_4.csv"

DELAY_BETWEEN_REQUESTS = 0.5   # seconds between requests
MAX_RETRIES            = 3     # retries on network errors / 5xx
RETRY_BACKOFF_500      = 2     # seconds between retries for 5xx (fast — server error, not rate limit)
RETRY_BACKOFF_NET      = 5     # seconds between retries for network errors

# ── Headers ────────────────────────────────────────────────────────────────────
def build_headers(token: str) -> dict:
    return {
        "accept": "*/*",
        "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
        "authorization": f"Bearer {token}",
        "origin": "https://climatemetrics.scientificratings.com",
        "referer": "https://climatemetrics.scientificratings.com/",
        "user-agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/151.0.0.0 Safari/537.36"
        ),
    }

# ── Token expiry check ─────────────────────────────────────────────────────────
def check_token_expiry(token: str):
    import base64, json
    try:
        payload = token.split(".")[1]
        payload += "=" * (4 - len(payload) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(payload))
        exp = decoded.get("exp", 0)
        remaining = exp - int(time.time())
        if remaining <= 0:
            print("⚠️  WARNING: Token is EXPIRED. Requests will return 401.")
        else:
            minutes = remaining // 60
            print(f"✅ Token valid for {minutes // 60}h {minutes % 60}m")
    except Exception:
        print("⚠️  Could not decode token — proceeding anyway.")

# ── Download one asset ─────────────────────────────────────────────────────────
def download_asset(session: requests.Session, asset_id: str, asset_name: str,
                   headers: dict, output_dir: Path) -> tuple[bool, int]:
    """
    Returns (success: bool, last_http_status: int).
    last_http_status is 0 for pure network errors.
    """
    url      = BASE_URL.format(id=asset_id)
    out_path = output_dir / f"{asset_name}_physical_risks.xlsx"

    # Skip already-downloaded files
    if out_path.exists():
        print(f"  ⏭  Skipping (already exists): {out_path.name}")
        return True, 200

    last_status = 0
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(url, headers=headers, timeout=60)
            last_status = resp.status_code

            if resp.status_code == 200:
                out_path.write_bytes(resp.content)
                size_kb = len(resp.content) / 1024
                print(f"  ✅ Saved {out_path.name}  ({size_kb:.1f} KB)")
                return True, 200

            elif resp.status_code == 401:
                print(f"  ❌ 401 Unauthorized — token expired. Aborting.")
                sys.exit(1)

            elif resp.status_code == 304:
                print(f"  ⏭  304 Not Modified: {asset_name}")
                return True, 304

            elif resp.status_code == 429:
                wait = int(resp.headers.get("Retry-After", 60))
                print(f"  ⏳ 429 Rate limited — waiting {wait}s ...")
                time.sleep(wait)
                # Don't count 429 as an attempt — retry immediately after wait
                attempt -= 1  # noqa — handled via loop continue

            else:
                # 5xx and other errors: short backoff, these are usually persistent
                print(f"  ⚠️  HTTP {resp.status_code} on attempt {attempt}/{MAX_RETRIES}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF_500)

        except requests.RequestException as e:
            print(f"  ⚠️  Network error on attempt {attempt}/{MAX_RETRIES}: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_NET)

    print(f"  ❌ Failed after {MAX_RETRIES} attempts: id={asset_id}, name={asset_name}")
    return False, last_status

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Bulk-download physical risk Excel exports.")
    parser.add_argument("--token",        default=DEFAULT_TOKEN, help="Bearer token override")
    parser.add_argument("--start-from",   type=int, default=0,   help="Skip first N assets (0-based resume)")
    parser.add_argument("--limit",        type=int, default=None, help="Only download N assets (for testing)")
    parser.add_argument("--retry-failed", action="store_true",   help="Re-run only assets listed in failed_assets.csv")
    args = parser.parse_args()

    check_token_expiry(args.token)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Load asset list ────────────────────────────────────────────────────────
    if args.retry_failed:
        if not FAILED_LOG.exists():
            print(f"❌ No failed_assets.csv found at {FAILED_LOG}")
            sys.exit(1)
        with open(FAILED_LOG, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            assets = [(row["id"], row["asset_name"]) for row in reader]
        print(f"\n🔁 Retrying {len(assets)} previously failed assets")
        # Overwrite the log fresh for this retry pass
        FAILED_LOG.unlink()
    else:
        with open(CSV_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            assets = [(row["id"], row["asset_name"]) for row in reader]

    total = len(assets)
    print(f"📋 Total assets to process : {total}")
    print(f"   Output directory        : {OUTPUT_DIR}")
    print(f"   Failure log             : {FAILED_LOG}\n")

    # Apply resume / limit (only for non-retry mode)
    if not args.retry_failed:
        assets = assets[args.start_from:]
        if args.limit:
            assets = assets[:args.limit]

    succeeded  = 0
    failed     = 0
    skipped    = 0
    fail_rows  = []
    headers    = build_headers(args.token)

    with requests.Session() as session:
        start_idx = args.start_from + 1 if not args.retry_failed else 1
        for i, (asset_id, asset_name) in enumerate(assets, start=start_idx):
            print(f"[{i}/{total}] id={asset_id}  {asset_name}")
            ok, status = download_asset(session, asset_id, asset_name, headers, OUTPUT_DIR)
            if ok:
                if status == 200 and not (OUTPUT_DIR / f"{asset_name}_physical_risks.xlsx").stat().st_size == 0:
                    succeeded += 1
                else:
                    skipped += 1
            else:
                failed += 1
                fail_rows.append({"id": asset_id, "asset_name": asset_name, "http_status": status})
            time.sleep(DELAY_BETWEEN_REQUESTS)

    # ── Write / append failure log ─────────────────────────────────────────────
    if fail_rows:
        write_header = not FAILED_LOG.exists()
        with open(FAILED_LOG, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["id", "asset_name", "http_status"])
            if write_header:
                writer.writeheader()
            writer.writerows(fail_rows)
        print(f"\n📝 Failures logged to: {FAILED_LOG}")
        print(f"   Re-run with: python3 {Path(__file__).name} --retry-failed [--token <new_JWT>]")

    print(f"\n{'='*60}")
    print(f"✅ Succeeded : {succeeded}")
    print(f"⏭  Skipped   : {skipped}  (already existed)")
    print(f"❌ Failed    : {failed}")
    print(f"📁 Files in  : {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
