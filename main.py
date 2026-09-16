"""
Site Documentation Bot — entry point.

Usage:
    1. cp .env.example .env   and fill in real values
    2. pip install -r requirements.txt
    3. playwright install chromium
    4. python main.py
"""
import os
import sys
from playwright.sync_api import sync_playwright

from config import Config
from login_handler import perform_login
from captcha_handler import check_and_wait_for_manual_solve
from crawler import crawl_site
from doc_generator import build_document
from progress import ProgressStore


def main():
    try:
        Config.validate()
    except ValueError as e:
        print(e)
        sys.exit(1)

    with sync_playwright() as p:
        browser_launcher = getattr(p, Config.BROWSER_TYPE)
        browser = browser_launcher.launch(headless=Config.HEADLESS)

        # Reuse saved session if present, to skip re-login/re-captcha on reruns
        context_kwargs = {
            "viewport": {"width": Config.VIEWPORT_WIDTH, "height": Config.VIEWPORT_HEIGHT}
        }
        if os.path.exists(Config.STORAGE_STATE_PATH):
            print(f"[main] Reusing saved session from {Config.STORAGE_STATE_PATH}")
            context_kwargs["storage_state"] = Config.STORAGE_STATE_PATH

        context = browser.new_context(**context_kwargs)
        page = context.new_page()

        # Step 1: login (if configured)
        if Config.LOGIN_URL and not os.path.exists(Config.STORAGE_STATE_PATH):
            perform_login(page)
            context.storage_state(path=Config.STORAGE_STATE_PATH)
            print(f"[main] Session saved to {Config.STORAGE_STATE_PATH}")
        elif Config.LOGIN_URL:
            print("[main] Skipping login — using saved session.")

        # Step 2: crawl
        store = crawl_site(page)

        browser.close()

    # Step 3: generate doc from everything accumulated in sqlite
    pages = store.all_done_pages() if isinstance(store, ProgressStore) else []
    if not pages:
        print("[main] No pages were successfully processed — nothing to document.")
        sys.exit(1)

    build_document(pages)
    print("[main] Done!")


if __name__ == "__main__":
    main()