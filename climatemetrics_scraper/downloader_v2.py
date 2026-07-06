#!/usr/bin/env python3
"""
ClimateMetrics Automation Script V2.
Logins into the ClimateMetrics platform, imports assets from a spreadsheet,
waits for the backend to analyze the assets, extracts the asset names,
and downloads the physical risk report files for each asset.
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
logger = logging.getLogger("climatemetrics_scraper_v2")

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
    "add_assets_button": "button:has-text('Add assets')",
    "browse_file_button": "xpath=/html/body/div[4]/div[3]/div[2]/div[2]/div[2]/button",
    "added_assets_section": "xpath=/html/body/div[2]/main/div/div/section",
    "continue_button": "xpath=/html/body/div[2]/main/div/div/header/div[2]/button[2]",
    "assets_tab": "xpath=/html/body/div[2]/div/div/div[1]/button[2]",
    "list_view_button": "xpath=/html/body/div[2]/main/div[1]/div[1]/div[2]/div/button[2]",
    "search_input": "xpath=/html/body/div[2]/main/div[1]/div[3]/div[1]/div[2]/div/div[1]/div/input",
    "first_asset_item": "xpath=/html/body/div[2]/main/div[1]/div[3]/div[2]/div/div[1]/div[1]",
    "export_button": "xpath=/html/body/div[3]/div[2]/div[2]/div/div/div/button[5]",
    "download_physical_risk_button": "xpath=/html/body/div[3]/div[2]/div[3]/div/div/div[1]/div[2]/button",
    "close_drawer_button": "xpath=/html/body/div[3]/div[2]/div[1]/button",
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
    import_file: Path,
    output_dir: Path,
    hold_multiplier: int = 180,
    headless: bool = True,
    timeout_ms: int = 30000
) -> bool:
    """Runs the web automation flow using Playwright sync API."""
    logger.info("Initializing Playwright...")
    
    # Ensure directories exist
    output_dir.mkdir(parents=True, exist_ok=True)
    failures_dir = output_dir / "failures"
    
    if not import_file.exists():
        logger.error(f"Error: Import file does not exist at {import_file}")
        return False
        
    success = False
    
    with sync_playwright() as p:
        # Launch browser
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
            logger.info("Waiting for redirect and main interface environment to load...")
            page.wait_for_load_state("networkidle")
            
            # 3. Add Assets Button click
            logger.info("Clicking the 'Add Assets' button...")
            page.wait_for_selector(SELECTORS["add_assets_button"], state="visible")
            page.click(SELECTORS["add_assets_button"])
            
            # 4. Browse File & Upload Flow
            logger.info(f"Locating browse file button and preparing to upload: {import_file}...")
            page.wait_for_selector(SELECTORS["browse_file_button"], state="visible")
            
            with page.expect_file_chooser() as fc_info:
                page.click(SELECTORS["browse_file_button"])
            file_chooser = fc_info.value
            file_chooser.set_files(import_file)
            
            # 5. Wait for assets section and load them
            logger.info("Waiting for assets to upload and populate section...")
            page.wait_for_selector(SELECTORS["added_assets_section"], state="visible")
            
            # Parse names of all successfully added assets
            logger.info("Extracting added asset names from list...")
            asset_names = []
            i = 1
            while True:
                selector = f"xpath=/html/body/div[2]/main/div/div/section/div[2]/div[{i}]/div/div[1]/div[1]"
                locator = page.locator(selector)
                
                # Check if elements are available
                if locator.count() > 0:
                    name = locator.text_content()
                    if name:
                        name_clean = name.strip()
                        if name_clean:
                            match = re.search(r'Asset name\s*:\s*(.*?)\s*(?=Asset type|Value|Revenues|Resilience|$)', name_clean, re.IGNORECASE)
                            extracted_name = match.group(1).strip() if match else name_clean
                            logger.info(f"Found uploaded asset {i}: '{name_clean}' -> Parsed name: '{extracted_name}'")
                            asset_names.append(extracted_name)
                    i += 1
                else:
                    # In case the first element takes a little while to render, wait and try once more
                    if i == 1:
                        logger.info("Waiting 2 seconds for first asset list item to render...")
                        page.wait_for_timeout(2000)
                        locator = page.locator(selector)
                        if locator.count() > 0:
                            continue
                    break
            
            if not asset_names:
                logger.error("No assets detected from the upload list!")
                failures_dir.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=failures_dir / "no_assets_extracted.png")
                return False
                
            logger.info(f"Successfully extracted {len(asset_names)} asset(s): {asset_names}")
            
            # 6. Click Continue
            logger.info("Clicking the 'Continue' button...")
            page.wait_for_selector(SELECTORS["continue_button"], state="visible")
            page.click(SELECTORS["continue_button"])
            
            # 7. Hold the pipeline for analysis
            num_assets = len(asset_names)
            wait_seconds = hold_multiplier * num_assets
            logger.info(f"Holding pipeline for analysis. Waiting {wait_seconds} seconds ({wait_seconds / 60:.1f} minutes) for {num_assets} asset(s)...")
            
            start_hold_time = time.time()
            while time.time() - start_hold_time < wait_seconds:
                elapsed = time.time() - start_hold_time
                remaining = wait_seconds - elapsed
                logger.info(f"Analysis hold active. Time remaining: {remaining:.0f}s...")
                page.wait_for_timeout(min(30, int(remaining)) * 1000)
            
            # 8. Click on Asset Tab & List view button to prepare for download stage
            logger.info("Navigating back to Assets list view...")
            page.wait_for_selector(SELECTORS["assets_tab"], state="visible")
            page.click(SELECTORS["assets_tab"])
            
            page.wait_for_selector(SELECTORS["list_view_button"], state="visible")
            page.click(SELECTORS["list_view_button"])
            
            # 9. Download Loop
            logger.info("Starting sequential download loop for each asset...")
            for idx, asset in enumerate(asset_names, 1):
                logger.info(f"[{idx}/{num_assets}] Processing asset: '{asset}'")
                
                # Input asset name in search box
                logger.info(f"Searching for asset: '{asset}'...")
                page.wait_for_selector(SELECTORS["search_input"], state="visible")
                page.fill(SELECTORS["search_input"], "")
                page.fill(SELECTORS["search_input"], asset)
                page.keyboard.press("Enter")
                
                # Wait for search results and list update
                page.wait_for_timeout(2000)
                page.wait_for_selector(SELECTORS["first_asset_item"], state="visible")
                
                # Click first asset from results to open drawer
                logger.info("Opening asset detail drawer...")
                page.click(SELECTORS["first_asset_item"])
                
                # Locate export button
                logger.info("Waiting for 'Export' button...")
                page.wait_for_selector(SELECTORS["export_button"], state="visible")
                page.click(SELECTORS["export_button"])
                
                # Locate download physical risk button
                logger.info("Waiting for 'Download Physical Risk' button...")
                page.wait_for_selector(SELECTORS["download_physical_risk_button"], state="visible")
                
                # Expect download & click
                logger.info("Triggering download of physical risk file...")
                with page.expect_download() as download_info:
                    page.click(SELECTORS["download_physical_risk_button"])
                
                download = download_info.value
                suggested_filename = download.suggested_filename
                suffix = Path(suggested_filename).suffix or ".xlsx"
                
                clean_name = sanitize_filename(asset)
                final_filename = f"{clean_name}{suffix}"
                final_path = output_dir / final_filename
                
                logger.info(f"Saving downloaded file to: {final_path}")
                download.save_as(final_path)
                logger.info(f"Successfully downloaded physical risk file for '{asset}' to: {final_path}")
                
                # Close the detail drawer
                logger.info("Closing detail drawer...")
                page.wait_for_selector(SELECTORS["close_drawer_button"], state="visible")
                page.click(SELECTORS["close_drawer_button"])
                
                # Refresh list view state
                logger.info("Resetting list view for next search...")
                page.wait_for_selector(SELECTORS["list_view_button"], state="visible")
                page.click(SELECTORS["list_view_button"])
                page.wait_for_timeout(1000)
                
            success = True
            logger.info("All downloads processed successfully!")
            
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
        description="Automate ClimateMetrics login, asset import from Excel, pipeline hold, and subsequent batch download of physical risk reports."
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
        "--import-file",
        default=str(Path(__file__).parent.parent / "docs" / "Untitled spreadsheet.xlsx"),
        help="Path to Excel spreadsheet containing assets to upload"
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).parent / "downloads"),
        help="Directory where downloaded asset reports will be stored"
    )
    parser.add_argument(
        "--hold-multiplier",
        type=int,
        default=180,
        help="Hold time in seconds per uploaded asset for analysis"
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
    import_file = Path(args.import_file)
    output_dir = Path(args.output_dir)
    hold_multiplier = args.hold_multiplier
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
    logger.info("Starting ClimateMetrics Downloader V2 Script")
    logger.info("========================================")
    logger.info(f"Email: {email}")
    logger.info(f"Import file: {import_file.resolve()}")
    logger.info(f"Output Directory: {output_dir.resolve()}")
    logger.info(f"Hold multiplier: {hold_multiplier}s per asset")
    
    success = run_scraper(
        email=email,
        password=password,
        import_file=import_file,
        output_dir=output_dir,
        hold_multiplier=hold_multiplier,
        headless=headless,
        timeout_ms=timeout_ms
    )
    
    if success:
        logger.info("V2 process completed successfully!")
        sys.exit(0)
    else:
        logger.error("V2 process failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
