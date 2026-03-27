# Google Photos Scraper

Bulk download your entire Google Photos library in original quality using browser automation. Built because Google killed the Photos API read scopes in March 2025 and Takeout is unreliable garbage.

## Why this exists

rclone for Google Photos backups has been broken since March 2025, and Google randomly bans entire Google accounts with zero recourse if their AI misclassifies something from your Google Photos account as illegal content, with zero recourse & zero human review.

## How it works

Uses SeleniumBase (undetected Chrome) to automate the Google Photos web UI:
1. Opens each photo in the viewer
2. Presses Shift+D (Google Photos' native download shortcut)
3. Reads EXIF metadata to organize files into `year/month/` folders
4. Saves progress to `.lastdone` for resume support

## Setup

```bash
pip install seleniumbase
python setup.py          # opens browser, log into Google Photos, close when done
```

## Usage

```bash
# Seed with your oldest photo URL
echo "https://photos.google.com/photo/YOUR_OLDEST_PHOTO_ID" > .lastdone

# Run with visible browser (recommended for first run)
python download.py --headed

# Run headless
python download.py

# Dry run (navigate without downloading)
python download.py --dry-run --headed
```

## Features

- Original quality downloads via Shift+D keyboard shortcut
- EXIF metadata date extraction (falls back to HTML parsing)
- Organized output: `downloads/year/month/filename.jpg`
- Resume support via `.lastdone` checkpoint file
- Retry logic: 3 attempts per photo with exponential backoff
- Human-realistic random delays (2-5s between downloads)
- Ctrl+C safe (saves progress on interrupt)
- Handles both photos and videos
