"""
Core crawl loop: BFS through internal links (or sitemap URLs),
extracting content and screenshots page by page, with captcha
pause-and-resume support baked in.
"""
import time
import os
from collections import deque
from urllib.parse import urlparse
from urllib import robotparser

from config import Config
from content_extractor import extract_page_data
from captcha_handler import check_and_wait_for_manual_solve
from summarizer import summarize_page
from progress import ProgressStore


def get_sitemap_urls(page, base_url: str, sitemap_url: str | None):
    """Try to fetch and parse a sitemap.xml for a more complete/efficient crawl seed."""
    candidates = []
    if sitemap_url:
        candidates.append(sitemap_url)
    candidates.append(base_url.rstrip("/") + "/sitemap.xml")

    for url in candidates:
        try:
            resp = page.request.get(url, timeout=8000)
            if resp.ok:
                text = resp.text()
                if "<urlset" in text or "<sitemapindex" in text:
                    import re
                    locs = re.findall(r"<loc>(.*?)</loc>", text)
                    if locs:
                        print(f"[crawler] Found {len(locs)} URLs in sitemap: {url}")
                        return locs
        except Exception:
            continue
    return []


def load_robots(base_url: str):
    rp = robotparser.RobotFileParser()
    try:
        rp.set_url(base_url.rstrip("/") + "/robots.txt")
        rp.read()
    except Exception:
        return None
    return rp


def is_excluded(url: str) -> bool:
    return any(frag in url for frag in Config.EXCLUDE_PATH_CONTAINS)


def crawl_site(page):
    """
    Runs the full crawl. Returns nothing directly — results are written
    incrementally to the ProgressStore (sqlite) so the run is resumable.
    """
    store = ProgressStore(Config.PROGRESS_DB_PATH)
    base_domain = urlparse(Config.BASE_URL).netloc
    robots = load_robots(Config.BASE_URL) if Config.RESPECT_ROBOTS_TXT else None

    os.makedirs(Config.SCREENSHOT_DIR, exist_ok=True)

    seed_urls = get_sitemap_urls(page, Config.BASE_URL, Config.SITEMAP_URL)
    if not seed_urls:
        seed_urls = [Config.BASE_URL]

    queue = deque(seed_urls)
    visited = set()
    processed_count = 0

    while queue and processed_count < Config.MAX_PAGES:
        url = queue.popleft()

        if url in visited:
            continue
        visited.add(url)

        if Config.SAME_DOMAIN_ONLY and urlparse(url).netloc != base_domain:
            continue
        if is_excluded(url):
            continue
        if robots and not robots.can_fetch("*", url):
            print(f"[crawler] Skipping (robots.txt disallows): {url}")
            continue
        if store.is_visited(url):
            print(f"[crawler] Already processed (resumed run), skipping: {url}")
            processed_count += 1
            continue

        print(f"[crawler] ({processed_count + 1}/{Config.MAX_PAGES}) Visiting: {url}")
        store.mark_queued(url)

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(500)

            # Check for captcha/MFA before reading content
            check_and_wait_for_manual_solve(page, context_label=url)

            html = page.content()
            extracted = extract_page_data(html, url, base_domain)

            screenshot_path = ""
            if Config.CAPTURE_SCREENSHOTS:
                safe_name = "".join(c if c.isalnum() else "_" for c in url)[-100:]
                screenshot_path = os.path.join(Config.SCREENSHOT_DIR, f"{safe_name}.png")
                try:
                    page.screenshot(path=screenshot_path, full_page=True)
                except Exception as e:
                    print(f"[crawler] Screenshot failed for {url}: {e}")
                    screenshot_path = ""

            summary = summarize_page(extracted)
            store.mark_done(url, extracted["title"], extracted, screenshot_path, summary)
            processed_count += 1

            for link in extracted["links"]:
                if link not in visited and not is_excluded(link):
                    queue.append(link)

        except Exception as e:
            print(f"[crawler] Failed to process {url}: {e}")
            store.mark_failed(url)

        time.sleep(Config.CRAWL_DELAY_SECONDS)

    print(f"[crawler] Done. Processed {processed_count} pages.")
    return store