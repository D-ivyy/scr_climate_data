# ClimateMetrics Automation Scraper

A robust web automation script built with Python and [Playwright](https://playwright.dev/python/) to automate logging in to ClimateMetrics, navigating to the list view, selecting the first active asset, opening the export menu, and downloading the physical asset risk report.

## Features
- **Headless & Headed Modes**: Run silently in headless mode (perfect for CI/CD pipelines) or headed mode (visual window for local debugging).
- **Graceful Error Handling**: Captures a full-page screenshot of the browser on timeout or unexpected error to help diagnose issues quickly.
- **Environment Integration**: Supports credentials via `.env` file or environment variables.
- **CLI-friendly**: Supports full parameter override via command-line arguments (perfect for dynamic parameter injection).
- **Sanitized Filename**: Extracts the text of the first asset, sanitizes it to be a valid filename, and saves the file named after the asset.

---

## Installation

1. Navigate to the scraper folder:
   ```bash
   cd climatemetrics_scraper
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install Playwright browser binaries (one-time setup):
   ```bash
   playwright install chromium
   ```

---

## Configuration

Duplicate `.env.example` as `.env` and fill in your actual credentials:

```bash
cp .env.example .env
```

Open `.env` and configure:
```env
CLIMATEMETRICS_EMAIL=your_email@example.com
CLIMATEMETRICS_PASSWORD=your_password_here

# Optional: Run in headless mode (true/false)
HEADLESS=true
```

---

## Usage

### 1. Default (Headless Mode)
Run the script to download the asset in the background. It reads credentials from `.env`:
```bash
python downloader.py
```

### 2. Headed Mode (Watch it run)
To visually inspect and debug what the browser is doing locally, pass `--headed` (or set `HEADLESS=false` in `.env`):
```bash
python downloader.py --headed
```

### 3. Command Line Argument Overrides
Provide credentials directly via arguments (useful for CI/CD pipelines):
```bash
python downloader.py --email "user@domain.com" --password "securepassword"
```

To configure a custom output directory for the downloads:
```bash
python downloader.py --output-dir "/path/to/custom/folder"
```

---

## Output Structure

- **Downloads**: By default, downloaded files are placed under `climatemetrics_scraper/downloads/` named after the selected asset (e.g., `Asset_Name_1.xlsx`).
- **Debugging & Failures**: If the script fails or times out, a screenshot of the browser state is automatically saved under `climatemetrics_scraper/downloads/failures/`.
