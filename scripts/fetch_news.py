"""Fetch candidate tech stories from Hacker News and RSS feeds (stdlib only)."""

import json
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

USER_AGENT = "daily-tech-post/1.0 (tech news curation script)"
HN_API = "https://hn.algolia.com/api/v1"
HTTP_TIMEOUT = 20
HTTP_ATTEMPTS = 3


def http_get(url, attempts=HTTP_ATTEMPTS):
    last_error = None
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
                return resp.read()
        except Exception as exc:  # noqa: BLE001 - network layer, log and retry
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"GET {url} failed after {attempts} attempts: {last_error}")


def _local_name(tag):
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _child_text(elem, names):
    for child in elem:
        if _local_name(child.tag) in names:
            text = (child.text or "").strip()
            if text:
                return text
    return None


def _child_link(elem):
    for child in elem:
        if _local_name(child.tag) == "link":
            href = child.get("href")
            if href:
                return href.strip()
            text = (child.text or "").strip()
            if text:
                return text
    return None


def _parse_feed_date(elem):
    raw = _child_text(elem, {"pubDate", "published", "updated", "date", "dc:date"})
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def fetch_hackernews(config, now):
    """Return candidates from the HN front page and recent popular stories."""
    cfg = config.get("sources", {}).get("hackernews", {})
    if not cfg.get("enabled", True):
        return []
    min_points = int(cfg.get("min_points", 75))
    hits_per_page = int(cfg.get("hits_per_page", 50))

    urls = [
        f"{HN_API}/search?tags=front_page&hitsPerPage=30",
        f"{HN_API}/search_by_date?tags=story"
        f"&numericFilters=points%3E{min_points}&hitsPerPage={hits_per_page}",
    ]
    candidates = {}
    for url in urls:
        data = json.loads(http_get(url))
        for hit in data.get("hits", []):
            object_id = hit.get("objectID")
            title = hit.get("title")
            link = hit.get("url")
            if not object_id or not title or not link:
                continue
            created = hit.get("created_at")
            published = (
                datetime.fromisoformat(created.replace("Z", "+00:00"))
                if created
                else now
            )
            candidates[object_id] = {
                "kind": "hn",
                "id": object_id,
                "title": " ".join(title.split()),
                "url": link,
                "source": "Hacker News",
                "points": int(hit.get("points") or 0),
                "comments": int(hit.get("num_comments") or 0),
                "hn_url": f"https://news.ycombinator.com/item?id={object_id}",
                "published": published,
                "min_points": min_points,
                "max_age_hours": int(cfg.get("max_age_hours", 48)),
            }
    return list(candidates.values())


def fetch_rss(feed_config, now):
    """Return candidates from a single RSS 2.0 or Atom feed."""
    name = feed_config.get("name", "RSS")
    url = feed_config["url"]
    max_age_hours = int(feed_config.get("max_age_hours", 36))
    root = ET.fromstring(http_get(url))
    cutoff = now - timedelta(hours=max_age_hours)

    candidates = []
    for elem in root.iter():
        if _local_name(elem.tag) not in ("item", "entry"):
            continue
        title = _child_text(elem, {"title"})
        link = _child_link(elem)
        if not title or not link:
            continue
        published = _parse_feed_date(elem) or now
        if published < cutoff:
            continue
        candidates.append(
            {
                "kind": "rss",
                "id": f"{name}:{link}",
                "title": " ".join(title.split()),
                "url": link,
                "source": name,
                "points": None,
                "comments": None,
                "hn_url": None,
                "published": published,
                "weight": int(feed_config.get("weight", 60)),
                "max_age_hours": max_age_hours,
            }
        )
    return candidates


def fetch_all(config, now=None):
    """Fetch all enabled sources. Raises if every source fails."""
    now = now or datetime.now(timezone.utc)
    all_candidates = []
    errors = []

    try:
        all_candidates.extend(fetch_hackernews(config, now))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"hackernews: {exc}")

    for feed in config.get("sources", {}).get("rss", []):
        if not feed.get("enabled", True):
            continue
        try:
            all_candidates.extend(fetch_rss(feed, now))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{feed.get('name', feed.get('url'))}: {exc}")

    for message in errors:
        print(f"WARN source failed: {message}")

    if not all_candidates:
        detail = "; ".join(errors) if errors else "sources returned nothing"
        raise RuntimeError(f"no candidates fetched ({detail})")

    print(f"fetched {len(all_candidates)} candidates ({len(errors)} source errors)")
    return all_candidates
