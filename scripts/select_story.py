"""Score candidates and pick the top story, excluding anything already posted."""

import json
import math
import urllib.parse
from datetime import datetime, timezone

TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term",
                   "utm_content", "fbclid", "gclid", "mc_cid", "mc_eid"}


def normalize_url(url):
    """Canonical form used for dedupe (drops tracking params, fragments, trailing /)."""
    if not url:
        return ""
    parts = urllib.parse.urlsplit(url.strip())
    query = urllib.parse.urlencode(
        [
            (k, v)
            for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=False)
            if k.lower() not in TRACKING_PARAMS
        ]
    )
    path = parts.path.rstrip("/")
    return urllib.parse.urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), path, query, "")
    )


def load_posted(state_path):
    """Return (norm_url set, object-id set) of previously posted stories."""
    try:
        with open(state_path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    urls, ids = set(), set()
    for entry in data.get("posted", []):
        if entry.get("norm_url"):
            urls.add(entry["norm_url"])
        if entry.get("id"):
            ids.add(str(entry["id"]))
    return urls, ids


def is_recently_posted(candidate, posted_urls, posted_ids):
    if str(candidate.get("id")) in posted_ids:
        return True
    return normalize_url(candidate["url"]) in posted_urls


def _freshness(published, now, max_age_hours):
    age_hours = (now - published).total_seconds() / 3600.0
    if age_hours < 0:
        age_hours = 0.0
    if age_hours >= max_age_hours:
        return None  # too old for this run's window
    return 1.0 - (age_hours / max_age_hours)


def score(candidate, now):
    """Return score, or None if the candidate fails age/quality filters."""
    if candidate["kind"] == "hn":
        max_age = candidate.get("max_age_hours", 48)
        if candidate.get("points", 0) < candidate.get("min_points", 0):
            return None
    else:
        max_age = candidate.get("max_age_hours", 36)

    freshness = _freshness(candidate["published"], now, max_age)
    if freshness is None:
        return None

    title = candidate.get("title") or ""
    url = candidate.get("url") or ""
    if len(title) < 15 or not url.startswith(("http://", "https://")):
        return None

    if candidate["kind"] == "hn":
        base = 10.0 * math.log2(1 + candidate.get("points", 0))
        base += 4.0 * math.log2(1 + candidate.get("comments", 0))
    else:
        base = float(candidate.get("weight", 60))

    return round(base * (0.55 + 0.45 * freshness), 3)


def dedupe_candidates(candidates):
    """One candidate per story URL; prefer the HN record (it has engagement data)."""
    best = {}
    for cand in candidates:
        key = normalize_url(cand["url"])
        existing = best.get(key)
        if existing is None or (existing["kind"] != "hn" and cand["kind"] == "hn"):
            best[key] = cand
    return list(best.values())


def select_story(candidates, config, state_path, now=None, top_n=5):
    """Return (chosen candidate, scored list of runners-up)."""
    now = now or datetime.now(timezone.utc)
    posted_urls, posted_ids = load_posted(state_path)

    scored = []
    for cand in dedupe_candidates(candidates):
        if is_recently_posted(cand, posted_urls, posted_ids):
            continue
        value = score(cand, now)
        if value is None:
            continue
        cand = dict(cand, score=value)
        scored.append(cand)

    scored.sort(key=lambda c: c["score"], reverse=True)
    if not scored:
        raise RuntimeError(
            "no eligible candidates (all too old, too weak, or already posted)"
        )
    return scored[0], scored[1:top_n + 1]
