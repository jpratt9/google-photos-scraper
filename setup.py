#!/usr/bin/env python3
"""Save Google Photos login session for headless downloading."""

import logging
import time

from utils import create_driver, setup_logging, SESSION_DIR, STAGING_DIR, GOOGLE_PHOTOS_URL


def main():
    setup_logging()
    log = logging.getLogger("setup")

    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    STAGING_DIR.mkdir(parents=True, exist_ok=True)

    log.info("Opening browser -- log in to Google Photos, then close the browser window")
    driver = create_driver(
        headed=True,
        user_data_dir=SESSION_DIR,
        download_dir=STAGING_DIR,
    )
    driver.get(GOOGLE_PHOTOS_URL)

    # Wait until user closes the browser
    while True:
        try:
            if not driver.window_handles:
                break
            time.sleep(1)
        except Exception:
            break

    log.info("Session saved to %s", SESSION_DIR)


if __name__ == "__main__":
    main()
