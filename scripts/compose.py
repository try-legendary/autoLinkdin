"""Render the selected story into LinkedIn-ready post text from config templates."""

import re


def _template_for(now, config):
    templates = config.get("post", {}).get("templates", {})
    day_key = now.strftime("%a").lower()
    return templates.get(day_key) or templates.get("default") or (
        "Tech story of the day:\n\n{title}\n{url}\n\n{detail}\n\n{hashtags}"
    )


def _detail_line(candidate):
    if candidate["kind"] == "hn":
        detail = (
            f"Featured on Hacker News - {candidate.get('points', 0)} points, "
            f"{candidate.get('comments', 0)} comments."
        )
        if candidate.get("hn_url"):
            detail += f"\nJoin the discussion: {candidate['hn_url']}"
        return detail
    return f"Via {candidate['source']}."


def _truncate(text, limit):
    if len(text) <= limit:
        return text
    suffix = "..."
    budget = limit - len(suffix)
    cut = text[:budget].rstrip()
    idx = cut.rfind(" ")
    if idx >= int(budget * 0.75):
        cut = cut[:idx].rstrip()
    return cut + suffix


def compose(candidate, config, now):
    post_cfg = config.get("post", {})
    max_length = int(post_cfg.get("max_length", 3000))
    hashtags = post_cfg.get("hashtags", "").strip()

    fields = {
        "title": candidate["title"],
        "url": candidate["url"],
        "source": candidate.get("source", ""),
        "detail": _detail_line(candidate),
        "hashtags": hashtags,
        "points": candidate.get("points") or 0,
        "comments": candidate.get("comments") or 0,
        "hn_url": candidate.get("hn_url") or "",
    }

    text = _template_for(now, config).format(**fields)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    if len(text) > max_length and hashtags and hashtags in text:
        text = re.sub(r"\n\n" + re.escape(hashtags) + r"\s*$", "", text).strip()
    if len(text) > max_length:
        text = _truncate(text, max_length)
    return text
