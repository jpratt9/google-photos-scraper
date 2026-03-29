# Google Photos Scraper

Bulk download your entire Google Photos library in original quality using browser automation. Built because Google killed the Photos API read scopes in March 2025 and Takeout is extremely unreliable.

## Why this exists

`rclone` for Google Photos backups has been broken since March 2025, and Google randomly bans entire Google accounts with zero recourse if their AI misclassifies something from your Google Photos account as illegal content, with zero recourse & zero human review. See [theywillbanyou.com](https://theywillbanyou.com) for real stories.

## How it works

Uses SeleniumBase (undetected Chrome) to automate the Google Photos web UI:
1. Opens each photo in the viewer
2. Presses Shift+D (Google Photos' native download shortcut)
3. Reads EXIF metadata to organize files into `year/month/` folders
4. Saves progress to `.lastdone` for resume support

## Setup

```bash
pip install seleniumbase
python setup.py              # opens browser, log into Google Photos, close when done
python setup.py --backward   # set up a second browser profile for backward worker
```

## Usage

```bash
# Seed with your oldest photo URL
echo "https://photos.google.com/photo/YOUR_OLDEST_PHOTO_ID" > .lastdone

# Run with visible browser (recommended for first run)
python download.py --headed

# Run headless
python download.py

# Run both workers simultaneously (2x speed)
python download.py --headed &             # forward: oldest -> newest
python download.py --headed --backward &  # backward: newest -> oldest

# Dry run (navigate without downloading)
python download.py --dry-run --headed
```

## Features

- Original quality downloads via Shift+D keyboard shortcut
- EXIF metadata date extraction (falls back to HTML parsing)
- Organized output: `downloads-2/year/month/filename.jpg`
- Resume support via `.lastdone` / `backward.lastdone` checkpoint files
- Two-worker mode: `--backward` flag runs a second browser (newest to oldest)
- Auto-extracts zip files returned by Google Photos into the correct folder
- Skip list: add URLs to `skiplist.txt` to skip specific photos/videos
- Retry logic: 3 attempts per photo with exponential backoff
- Human-realistic random delays (1-3s between downloads)
- Error resilience: Chrome timeouts don't crash the script
- Ctrl+C safe (saves progress on interrupt)
- Handles photos, videos, and zip bundles
