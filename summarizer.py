"""
Optional LLM step: turns raw extracted page data into a clean,
documentation-style summary of the page's features.
"""
from config import Config

_client = None


def _get_client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic(api_key=Config.ANTHROPIC_API_KEY)
    return _client


SYSTEM_PROMPT = (
    "You are a technical writer producing precise, factual software "
    "documentation from scraped web page content. You will be given the "
    "title, headings, visible text, form fields, and buttons found on one "
    "page of a website. Write a concise documentation section for this page "
    "in Markdown with this structure:\n\n"
    "### <Page purpose / feature name>\n"
    "- **What it does:** ...\n"
    "- **Key elements:** (forms, buttons, inputs found, described by function)\n"
    "- **How a user interacts with it:** ...\n\n"
    "Only describe what is actually present in the given content — never "
    "invent features. If the page is boilerplate (e.g. a legal/footer page) "
    "with no real product feature, say so briefly in one line instead of "
    "forcing the template."
)


def summarize_page(extracted: dict) -> str:
    if not Config.USE_LLM_SUMMARY:
        return _fallback_summary(extracted)

    client = _get_client()
    user_content = (
        f"URL: {extracted['url']}\n"
        f"Title: {extracted['title']}\n"
        f"Headings: {extracted['headings']}\n"
        f"Forms: {extracted['forms']}\n"
        f"Buttons: {extracted['buttons']}\n"
        f"Visible text (truncated): {extracted['main_text']}\n"
    )

    try:
        response = client.messages.create(
            model=Config.ANTHROPIC_MODEL,
            max_tokens=600,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        parts = [b.text for b in response.content if getattr(b, "type", "") == "text"]
        return "\n".join(parts).strip() or _fallback_summary(extracted)
    except Exception as e:
        print(f"[summarizer] LLM call failed ({e}); using fallback summary.")
        return _fallback_summary(extracted)


def _fallback_summary(extracted: dict) -> str:
    lines = [f"### {extracted['title'] or extracted['url']}"]
    if extracted["headings"]:
        lines.append("**Headings found:**")
        for h in extracted["headings"][:15]:
            lines.append(f"- ({h['level']}) {h['text']}")
    if extracted["forms"]:
        lines.append("**Forms found:**")
        for f in extracted["forms"]:
            field_names = ", ".join(fl["name"] or fl["type"] for fl in f["fields"]) or "no named fields"
            lines.append(f"- Form → {field_names}")
    if extracted["buttons"]:
        lines.append(f"**Buttons/actions:** {', '.join(extracted['buttons'][:20])}")
    if extracted["main_text"]:
        snippet = extracted["main_text"][:400]
        lines.append(f"**Text excerpt:** {snippet}...")
    return "\n".join(lines)