"""
Loads configuration from .env. Only BASE_URL/LOGIN_URL/credentials are
meant to be set by the user — everything below that is a sensible
default a normal run doesn't need to touch. Advanced users can still
override any of them by adding the same var name to .env.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # --- Required-ish ---
    BASE_URL = os.getenv("BASE_URL", "").rstrip("/")
    LOGIN_URL = os.getenv("LOGIN_URL", "").strip()
    LOGIN_EMAIL = os.getenv("LOGIN_EMAIL", "")
    LOGIN_PASSWORD = os.getenv("LOGIN_PASSWORD", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

    # --- Everything below: sane defaults, rarely need changing ---
    SITEMAP_URL = os.getenv("SITEMAP_URL", "").strip()

    MAX_PAGES = int(os.getenv("MAX_PAGES", "150"))
    CRAWL_DELAY_SECONDS = float(os.getenv("CRAWL_DELAY_SECONDS", "1.5"))
    RESPECT_ROBOTS_TXT = os.getenv("RESPECT_ROBOTS_TXT", "true").lower() == "true"
    SAME_DOMAIN_ONLY = os.getenv("SAME_DOMAIN_ONLY", "true").lower() == "true"
    EXCLUDE_PATH_CONTAINS = [
        p.strip() for p in os.getenv(
            "EXCLUDE_PATH_CONTAINS",
            "/privacy,/terms,/cookie-policy,/legal,/careers,/blog"
        ).split(",") if p.strip()
    ]

    # Headless is forced off automatically when a captcha is detected,
    # but default to visible so you can watch/intervene from the start.
    HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
    BROWSER_TYPE = os.getenv("BROWSER_TYPE", "chromium")
    VIEWPORT_WIDTH = int(os.getenv("VIEWPORT_WIDTH", "1440"))
    VIEWPORT_HEIGHT = int(os.getenv("VIEWPORT_HEIGHT", "900"))

    STORAGE_STATE_PATH = os.getenv("STORAGE_STATE_PATH", "storage_state.json")

    CAPTURE_SCREENSHOTS = os.getenv("CAPTURE_SCREENSHOTS", "true").lower() == "true"
    SCREENSHOT_DIR = os.getenv("SCREENSHOT_DIR", "screenshots")

    USE_LLM_SUMMARY = bool(ANTHROPIC_API_KEY)  # auto-enabled if a key is provided
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")

    OUTPUT_DOCX_PATH = os.getenv("OUTPUT_DOCX_PATH", "output/site_documentation.docx")
    PROGRESS_DB_PATH = os.getenv("PROGRESS_DB_PATH", "progress.sqlite3")

    @classmethod
    def validate(cls):
        errors = []
        if not cls.BASE_URL:
            errors.append("BASE_URL is required in .env")
        if cls.LOGIN_URL and (not cls.LOGIN_EMAIL or not cls.LOGIN_PASSWORD):
            errors.append("LOGIN_URL is set but LOGIN_EMAIL/LOGIN_PASSWORD are missing")
        if errors:
            raise ValueError("Config errors:\n- " + "\n- ".join(errors))