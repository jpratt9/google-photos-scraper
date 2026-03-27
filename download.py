#!/usr/bin/env python3
"""Download all Google Photos in original quality via browser automation."""

import argparse
import logging
import sys
import time

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from utils import (
    create_driver, setup_logging, read_progress, save_progress, clean_url,
    organize_file, wait_for_download, human_delay,
    SESSION_DIR, DOWNLOADS_DIR, STAGING_DIR, LASTDONE_FILE,
    GOOGLE_PHOTOS_URL, MAX_RETRIES, RETRY_BACKOFF_BASE,
    DOWNLOAD_TIMEOUT,
)

log = logging.getLogger("download")


def get_latest_photo(driver):
    """Navigate to Google Photos and find the latest (most recent) photo URL."""
    driver.get(GOOGLE_PHOTOS_URL)
    time.sleep(3)
    ActionChains(driver).send_keys(Keys.ARROW_RIGHT).perform()
    time.sleep(1)
    url = driver.execute_script(
        "return document.activeElement.href || document.activeElement.toString()"
    )
    return url


def trigger_download(driver):
    """Press Shift+D to trigger Google Photos' native download."""
    ActionChains(driver).key_down(Keys.SHIFT).send_keys("d").key_up(Keys.SHIFT).perform()


def download_single(driver, staging_dir, downloads_dir, overwrite=False):
    """Download the currently viewed photo/video with retry logic."""
    for attempt in range(MAX_RETRIES):
        try:
            known = set(staging_dir.iterdir())
            trigger_download(driver)
            downloaded = wait_for_download(staging_dir, DOWNLOAD_TIMEOUT, known)
            final_path = organize_file(downloaded, downloads_dir, driver, overwrite=overwrite)
            return "ok", final_path
        except TimeoutError:
            if attempt < MAX_RETRIES - 1:
                backoff = RETRY_BACKOFF_BASE ** attempt
                log.warning(
                    "Download timeout (attempt %d/%d), retrying in %ds: %s",
                    attempt + 1, MAX_RETRIES, backoff, driver.current_url,
                )
                time.sleep(backoff)
            else:
                log.error(
                    "Download failed after %d attempts: %s",
                    MAX_RETRIES, driver.current_url,
                )
                return "failed", None
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                backoff = RETRY_BACKOFF_BASE ** attempt
                log.warning(
                    "Download error (attempt %d/%d): %s — retrying in %ds",
                    attempt + 1, MAX_RETRIES, e, backoff,
                )
                time.sleep(backoff)
            else:
                log.error(
                    "Download failed after %d attempts: %s — %s",
                    MAX_RETRIES, driver.current_url, e,
                )
                return "failed", None
    return "failed", None


def navigate_next(driver, current_url, timeout=30):
    """Navigate to the next (newer) photo by clicking 'View previous photo' div.

    Google Photos shows oldest-to-newest as right-to-left, so going forward
    in time means clicking the 'previous' arrow (left arrow / back in the viewer).
    """
    strategies = [
        # Strategy 1: Click the 'View previous photo' div via JS
        lambda: driver.execute_script("""
            var selectors = [
                '[aria-label="View previous photo"]',
                '[aria-label="View previous video"]',
                '[aria-label="View previous"]',
            ];
            for (var sel of selectors) {
                var el = document.querySelector(sel);
                if (el) { el.click(); return true; }
            }
            // Fallback: find any div with 'previous' in aria-label
            var divs = document.querySelectorAll('div[aria-label]');
            for (var div of divs) {
                if (div.getAttribute('aria-label').toLowerCase().includes('previous')) {
                    div.click(); return true;
                }
            }
            return false;
        """),
        # Strategy 2: Keyboard left arrow on body
        lambda: (driver.execute_script("document.body.focus()"),
                 ActionChains(driver).send_keys(Keys.ARROW_LEFT).perform()),
        # Strategy 3: Direct keyboard press via JS
        lambda: driver.execute_script("""
            document.dispatchEvent(new KeyboardEvent('keydown', {key: 'ArrowLeft', bubbles: true}));
        """),
    ]

    for i, strategy in enumerate(strategies):
        try:
            strategy()
        except Exception:
            continue

        # Wait for URL change
        for _ in range(timeout * 2):
            new_url = driver.current_url
            if clean_url(new_url) != clean_url(current_url):
                return True
            time.sleep(0.5)

        log.debug("Strategy %d didn't navigate, trying next", i + 1)

    return False


def main():
    parser = argparse.ArgumentParser(description="Download Google Photos")
    parser.add_argument("--headed", action="store_true", help="Run with visible browser")
    parser.add_argument("--dry-run", action="store_true", help="Navigate but don't download")
    args = parser.parse_args()

    setup_logging()

    if not SESSION_DIR.exists():
        log.error("No session found. Run setup.py first.")
        sys.exit(1)

    start_url = read_progress(LASTDONE_FILE)
    log.info("Resuming from: %s", start_url)

    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    STAGING_DIR.mkdir(parents=True, exist_ok=True)

    driver = create_driver(
        headed=args.headed,
        user_data_dir=SESSION_DIR,
        download_dir=STAGING_DIR,
    )

    stats = {"downloaded": 0, "skipped": 0, "failed": 0}

    try:
        # Find the latest photo as stopping condition
        latest_url = get_latest_photo(driver)
        log.info("Latest photo: %s", latest_url)
        log.info("---")

        # Navigate to starting point
        driver.get(start_url)
        time.sleep(3)

        # Download first photo (overwrite OK — may be resume point)
        if not args.dry_run:
            status, path = download_single(driver, STAGING_DIR, DOWNLOADS_DIR, overwrite=True)
            if status == "ok":
                stats["downloaded"] += 1
                log.info("[%d] %s", stats["downloaded"], path.name)
            elif status == "failed":
                stats["failed"] += 1

        # Navigate forward through all photos
        while True:
            current_url = driver.current_url

            # Check if we've reached the end
            if clean_url(current_url) == clean_url(latest_url):
                log.info("Reached latest photo, done!")
                break

            # Check for unexpected navigation (login page, etc.)
            if "photos.google.com" not in current_url:
                log.error("Navigated away from Google Photos: %s", current_url)
                log.error("Session may have expired. Re-run setup.py to log in again.")
                break

            if not navigate_next(driver, current_url):
                log.error("Navigation stuck at %s", current_url)
                break

            if args.dry_run:
                total = stats["downloaded"] + stats["skipped"] + stats["failed"] + 1
                log.info("[dry-run] [%d] %s", total, driver.current_url)
                human_delay()
                continue

            status, path = download_single(driver, STAGING_DIR, DOWNLOADS_DIR, overwrite=False)
            if status == "ok":
                stats["downloaded"] += 1
                log.info("[%d] %s", stats["downloaded"], path.name)
            elif status == "failed":
                stats["failed"] += 1
                log.warning("FAILED: %s", driver.current_url)

            save_progress(LASTDONE_FILE, driver.current_url)
            human_delay()

            # Progress report every 50 photos
            total = stats["downloaded"] + stats["failed"]
            if total > 0 and total % 50 == 0:
                log.info(
                    "--- Progress: %d downloaded, %d failed ---",
                    stats["downloaded"], stats["failed"],
                )

    except KeyboardInterrupt:
        log.info("Interrupted by user. Progress saved.")
        save_progress(LASTDONE_FILE, driver.current_url)
    finally:
        log.info(
            "FINAL: %d downloaded, %d failed",
            stats["downloaded"], stats["failed"],
        )
        driver.quit()


if __name__ == "__main__":
    main()
