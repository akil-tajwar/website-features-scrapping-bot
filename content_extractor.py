"""
Extracts structured content from a rendered page: headings, main text,
forms/inputs, buttons, and internal links (for further crawling).
"""
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


BOILERPLATE_TAGS = ["script", "style", "noscript", "svg"]


def extract_page_data(html: str, page_url: str, base_domain: str):
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(BOILERPLATE_TAGS):
        tag.decompose()

    title = (soup.title.string.strip() if soup.title and soup.title.string else "").strip()

    headings = []
    for level in ["h1", "h2", "h3", "h4"]:
        for h in soup.find_all(level):
            text = h.get_text(strip=True)
            if text:
                headings.append({"level": level, "text": text})

    # Main text: prefer <main>, fall back to <body>
    main_el = soup.find("main") or soup.body
    main_text = ""
    if main_el:
        main_text = " ".join(main_el.get_text(separator=" ", strip=True).split())
        main_text = main_text[:6000]  # cap per-page raw text sent onward

    forms = []
    for form in soup.find_all("form"):
        fields = []
        for inp in form.find_all(["input", "select", "textarea"]):
            fields.append({
                "tag": inp.name,
                "type": inp.get("type", ""),
                "name": inp.get("name", ""),
                "placeholder": inp.get("placeholder", ""),
            })
        forms.append({
            "action": form.get("action", ""),
            "method": form.get("method", "get"),
            "fields": fields,
        })

    buttons = []
    for btn in soup.find_all(["button"]):
        text = btn.get_text(strip=True)
        if text:
            buttons.append(text)
    for inp in soup.find_all("input", {"type": ["button", "submit"]}):
        val = inp.get("value", "")
        if val:
            buttons.append(val)

    # Internal links for crawl queue
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
            continue
        absolute = urljoin(page_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in ("http", "https"):
            continue
        # strip fragment
        clean = parsed._replace(fragment="").geturl()
        if parsed.netloc == base_domain:
            links.add(clean)

    return {
        "url": page_url,
        "title": title,
        "headings": headings,
        "main_text": main_text,
        "forms": forms,
        "buttons": list(set(buttons)),
        "links": list(links),
    }