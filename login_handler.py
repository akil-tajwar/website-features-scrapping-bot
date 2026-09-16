"""
Logs into the target site using credentials from .env — no CSS
selectors required. It tries a list of common patterns for email,
password, and submit buttons, and handles both single-page login
forms and two-step ones (email first -> continue -> password screen),
which is how many SaaS sites (including Teamwork) work.
"""
from config import Config
from captcha_handler import check_and_wait_for_manual_solve

EMAIL_CANDIDATES = [
    'input[type="email"]',
    'input[name="email"]',
    'input[name="username"]',
    'input[id*="email" i]',
    'input[autocomplete="username"]',
]

PASSWORD_CANDIDATES = [
    'input[type="password"]',
    'input[name="password"]',
    'input[id*="password" i]',
]

CONTINUE_CANDIDATES = [
    'button:has-text("Continue")',
    'button:has-text("Next")',
    'button[type="submit"]',
    'input[type="submit"]',
]

SUBMIT_CANDIDATES = [
    'button:has-text("Log in")',
    'button:has-text("Login")',
    'button:has-text("Sign in")',
    'button[type="submit"]',
    'input[type="submit"]',
]


def _first_visible(page, selectors, timeout=4000):
    """Returns the first selector from the list that matches a visible element, or None."""
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            loc.wait_for(state="visible", timeout=timeout)
            return sel
        except Exception:
            continue
    return None


def perform_login(page) -> bool:
    if not Config.LOGIN_URL:
        print("[login] No LOGIN_URL configured — skipping login.")
        return True

    print(f"[login] Navigating to {Config.LOGIN_URL}")
    page.goto(Config.LOGIN_URL, wait_until="domcontentloaded")
    check_and_wait_for_manual_solve(page, context_label="login page")

    # --- Step 1: email ---
    email_sel = _first_visible(page, EMAIL_CANDIDATES)
    if not email_sel:
        print("[login] Couldn't auto-detect an email field.")
        input("[login] Please log in manually in the browser window, then press Enter here...")
        return True

    page.fill(email_sel, Config.LOGIN_EMAIL)

    # Is the password field already on this page, or is this a two-step flow?
    password_sel = _first_visible(page, PASSWORD_CANDIDATES, timeout=1500)

    if not password_sel:
        # Two-step: click continue/next to reveal the password field
        cont_sel = _first_visible(page, CONTINUE_CANDIDATES, timeout=3000)
        if cont_sel:
            page.click(cont_sel)
            page.wait_for_load_state("networkidle", timeout=10000)
            check_and_wait_for_manual_solve(page, context_label="after email step")
            password_sel = _first_visible(page, PASSWORD_CANDIDATES, timeout=6000)

    if not password_sel:
        print("[login] Couldn't auto-detect a password field after email step.")
        input("[login] Please finish logging in manually, then press Enter here...")
        return True

    # --- Step 2: password ---
    page.fill(password_sel, Config.LOGIN_PASSWORD)

    submit_sel = _first_visible(page, SUBMIT_CANDIDATES, timeout=3000)
    if submit_sel:
        page.click(submit_sel)
    else:
        page.keyboard.press("Enter")

    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except Exception:
        pass

    # Captcha/MFA often appears right after submitting credentials
    check_and_wait_for_manual_solve(page, context_label="post-submit")

    print("[login] Login flow complete (or handed off to you for manual finish).")
    return True