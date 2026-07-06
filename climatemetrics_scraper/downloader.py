#!/usr/bin/env python3
"""
ClimateMetrics Automation Script.
Logins into the ClimateMetrics platform, navigates to assets,
selects the first asset, and exports/downloads the file.
"""

import os
import re
import sys
import time
import logging
import argparse
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("climatemetrics_scraper")

# Load environment variables (check local directory first, then parent)
local_env = Path(__file__).parent / ".env"
parent_env = Path(__file__).parent.parent / ".env"
if local_env.exists():
    load_dotenv(dotenv_path=local_env)
    logger.info(f"Loaded environment variables from local env: {local_env}")
elif parent_env.exists():
    load_dotenv(dotenv_path=parent_env)
    logger.info(f"Loaded environment variables from parent env: {parent_env}")
else:
    load_dotenv()
    logger.info("Loaded system environment variables.")

# Target URL
TARGET_URL = "https://climatemetrics.scientificratings.com/login?redirect=%2Fassets%3Flist%3Dtrue"

# Selectors (provided XPaths)
SELECTORS = {
    "email_input": "xpath=/html/body/div[2]/div[1]/form/div/div[2]/div/div/input",
    "password_input": "xpath=/html/body/div[2]/div[1]/form/div/div[3]/div/div/input",
    "submit_button": "xpath=/html/body/div[2]/div[1]/form/div/div[4]/button",
    "list_view_button": "xpath=/html/body/div[2]/main/div[1]/div[1]/div[2]/div/button[2]",
    "first_asset_item": "xpath=/html/body/div[2]/main/div[1]/div[3]/div[2]/div/div[1]/div[1]",
    "export_button": "xpath=/html/body/div[3]/div[2]/div[2]/div/div/div/button[5]",
    "download_physical_risk_button": "xpath=/html/body/div[3]/div[2]/div[3]/div/div/div[1]/div[2]/button",
}

def sanitize_filename(name: str) -> str:
    """Sanitizes a string to make it a safe and valid filename."""
    if not name:
        return "asset_export"
    # Remove leading/trailing whitespaces and normalize internal ones
    name = " ".join(name.strip().split())
    # Remove characters that are unsafe for filenames
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    # Replace spaces and hyphens with underscores
    name = re.sub(r'[-\s]+', "_", name)
    return name

def run_scraper(
    email: str,
    password: str,
    output_dir: Path,
    headless: bool = True,
    timeout_ms: int = 30000
) -> bool:
    """Runs the web automation flow using Playwright sync API."""
    logger.info("Initializing Playwright...")
    
    # Ensure directories exist
    output_dir.mkdir(parents=True, exist_ok=True)
    failures_dir = output_dir / "failures"
    
    success = False
    
    with sync_playwright() as p:
        # Launch browser (Chromium is highly standard and performant)
        logger.info(f"Launching browser (headless={headless})...")
        browser = p.chromium.launch(headless=headless)
        
        # Create context and page
        context = browser.new_context(
            accept_downloads=True,
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()
        page.set_default_timeout(timeout_ms)
        
        try:
            # 1. Open Target URL
            logger.info(f"Navigating to {TARGET_URL}...")
            page.goto(TARGET_URL)
            page.wait_for_load_state("networkidle")
            
            # 2. Login Flow
            logger.info("Filling login credentials...")
            page.wait_for_selector(SELECTORS["email_input"], state="visible")
            page.fill(SELECTORS["email_input"], email)
            page.fill(SELECTORS["password_input"], password)
            
            logger.info("Submitting login form...")
            page.click(SELECTORS["submit_button"])
            
            # Wait for redirect and main content to load
            logger.info("Waiting for redirect and asset list view environment to load...")
            page.wait_for_load_state("networkidle")
            
            # 3. Hit the List view button
            logger.info("Clicking the List view button...")
            page.wait_for_selector(SELECTORS["list_view_button"], state="visible")
            page.click(SELECTORS["list_view_button"])
            
            # 4. Extract asset name and click the first asset
            logger.info("Locating the first asset in the list...")
            page.wait_for_selector(SELECTORS["first_asset_item"], state="visible")
            
            # Get text description of asset to use as download name
            raw_asset_name = page.locator(SELECTORS["first_asset_item"]).text_content()
            clean_name = sanitize_filename(raw_asset_name)
            logger.info(f"Detected first asset name: '{raw_asset_name}' -> Sanitize to file prefix: '{clean_name}'")
            
            # Click the asset
            logger.info("Clicking on the first asset...")
            page.click(SELECTORS["first_asset_item"])
            
            # 5. Export / Download
            logger.info("Locating export button inside the detail view...")
            page.wait_for_selector(SELECTORS["export_button"], state="visible")
            
            logger.info("Clicking export button to open download menu...")
            page.click(SELECTORS["export_button"])
            
            logger.info("Locating physical asset risk download button...")
            page.wait_for_selector(SELECTORS["download_physical_risk_button"], state="visible")
            
            # Start waiting for download before clicking the physical asset risk download button
            logger.info("Clicking download button and waiting for file download...")
            with page.expect_download() as download_info:
                page.click(SELECTORS["download_physical_risk_button"])
                
            download = download_info.value
            suggested_filename = download.suggested_filename
            suffix = Path(suggested_filename).suffix or ".xlsx"
            
            final_filename = f"{clean_name}{suffix}"
            final_path = output_dir / final_filename
            
            logger.info(f"Download triggered successfully. Suggested: {suggested_filename}. Suffix: {suffix}")
            logger.info(f"Saving downloaded file to: {final_path}")
            
            download.save_as(final_path)
            logger.info(f"Successfully exported asset file to: {final_path}")
            success = True
            
        except PlaywrightTimeoutError as te:
            logger.error(f"Timeout occurred during automation step: {te}")
            failures_dir.mkdir(parents=True, exist_ok=True)
            screenshot_path = failures_dir / f"failure_timeout_{int(time.time())}.png"
            page.screenshot(path=screenshot_path)
            logger.info(f"Screenshot saved to: {screenshot_path}")
        except Exception as e:
            logger.error(f"An unexpected error occurred: {e}")
            failures_dir.mkdir(parents=True, exist_ok=True)
            screenshot_path = failures_dir / f"failure_error_{int(time.time())}.png"
            page.screenshot(path=screenshot_path)
            logger.info(f"Screenshot saved to: {screenshot_path}")
        finally:
            context.close()
            browser.close()
            logger.info("Browser closed.")
            
    return success

def main():
    parser = argparse.ArgumentParser(
        description="Automate ClimateMetrics login and download the first asset file."
    )
    parser.add_argument(
        "--email",
        default=os.getenv("CLIMATEMETRICS_EMAIL"),
        help="Email credential (or specify CLIMATEMETRICS_EMAIL in .env)"
    )
    parser.add_argument(
        "--password",
        default=os.getenv("CLIMATEMETRICS_PASSWORD"),
        help="Password credential (or specify CLIMATEMETRICS_PASSWORD in .env)"
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).parent / "downloads"),
        help="Directory where the downloaded asset will be stored"
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser in headed mode (visible browser window for debugging)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Page step timeout in seconds"
    )

    args = parser.parse_args()

    # Validate inputs
    email = args.email
    password = args.password
    output_dir = Path(args.output_dir)
    headless = not args.headed
    timeout_ms = args.timeout * 1000

    if not email or email == "your-email-here@domain.com":
        logger.error("Error: Missing Email. Please specify via --email or set CLIMATEMETRICS_EMAIL in .env")
        sys.exit(1)
    if not password or password == "your-password-here":
        logger.error("Error: Missing Password. Please specify via --password or set CLIMATEMETRICS_PASSWORD in .env")
        sys.exit(1)

    # Convert HEADLESS setting from env if CLI flag wasn't provided
    env_headless = os.getenv("HEADLESS", "true").lower()
    if env_headless == "false":
        headless = False

    logger.info("========================================")
    logger.info("Starting ClimateMetrics Downloader Script")
    logger.info("========================================")
    logger.info(f"Email: {email}")
    logger.info(f"Output Directory: {output_dir.resolve()}")
    
    success = run_scraper(
        email=email,
        password=password,
        output_dir=output_dir,
        headless=headless,
        timeout_ms=timeout_ms
    )
    
    if success:
        logger.info("Process completed successfully!")
        sys.exit(0)
    else:
        logger.error("Process failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
