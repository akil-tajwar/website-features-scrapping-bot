"""
Detects common captcha/verification patterns on a page and pauses
execution so the human user can solve it manually in the visible
browser window before the bot resumes.
"""

CAPTCHA_SELECTORS = [
    "iframe[src*='recaptcha']",
    "iframe[src*='hcaptcha']",
    "iframe[title*='captcha' i]",
    "div.g-recaptcha",
    "div.h-captcha",
    "#cf-challenge-running",       # Cloudflare challenge
    "div[id*='captcha' i]",
    "form[action*='captcha' i]",
]

MFA_HINT_SELECTORS = [
    "input[name*='otp' i]",
    "input[autocomplete='one-time-code']",
    "text=Verification code",
    "text=Two-factor",
]


def check_and_wait_for_manual_solve(page, context_label: str = ""):
    """
    Checks the current page for captcha/MFA patterns.
    If found, alerts the user in the terminal and blocks until
    they confirm it's solved. Safe no-op if nothing is detected.
    """
    detected = None

    for sel in CAPTCHA_SELECTORS:
        try:
            if page.locator(sel).count() > 0:
                detected = ("CAPTCHA", sel)
                break
        except Exception:
            continue

    if not detected:
        for sel in MFA_HINT_SELECTORS:
            try:
                if page.locator(sel).count() > 0:
                    detected = ("MFA / verification step", sel)
                    break
            except Exception:
                continue

    if detected:
        kind, sel = detected
        print("\n" + "=" * 60)
        print(f"  MANUAL ACTION REQUIRED: {kind} detected")
        if context_label:
            print(f"  Page: {context_label}")
        print(f"  Matched selector: {sel}")
        print("  A browser window should be visible (HEADLESS=false).")
        print("  Please solve it there, then come back here.")
        print("=" * 60)
        input("Press Enter once you've resolved it to continue crawling...\n")
        # Give the page a moment to settle/redirect after solving
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        return True

    return False