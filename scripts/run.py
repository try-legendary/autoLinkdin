"""Daily pipeline: fetch news -> select story -> compose -> publish to Buffer.

Usage:
    python3 scripts/run.py --dry-run
    python3 scripts/run.py --test          # full run against a mocked Buffer API
    python3 scripts/run.py                 # publishes (needs Buffer env vars)
    DRY_RUN=true python3 scripts/run.py    # same as --dry-run (used by GitHub Actions)
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fetch_news import fetch_all  # noqa: E402
from select_story import normalize_url, select_story  # noqa: E402
from compose import compose  # noqa: E402
from publish import create_post  # noqa: E402
from mock_buffer import MockBufferTransport  # noqa: E402


def load_config(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save_state(state_path, entry):
    try:
        with open(state_path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    data.setdefault("posted", []).append(entry)
    with open(state_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def env_flag(name):
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def main():
    parser = argparse.ArgumentParser(description="Run the daily tech post pipeline")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true",
                      help="run everything except publishing")
    mode.add_argument("--test", action="store_true",
                      help="full run including publish, against a mocked Buffer API")
    parser.add_argument("--config", default=str(ROOT / "config.json"))
    parser.add_argument("--state", default=None,
                        help="state file (default: posted.json, or posted.test.json "
                             "in --test mode)")
    parser.add_argument("--show", type=int, default=5,
                        help="number of top candidates to print")
    args = parser.parse_args()

    test_mode = args.test
    dry_run = (args.dry_run or env_flag("DRY_RUN")) and not test_mode
    state_path = args.state or str(
        ROOT / "state" / ("posted.test.json" if test_mode else "posted.json")
    )
    now = datetime.now(timezone.utc)
    config = load_config(args.config)

    print(f"== daily tech post pipeline ({now:%Y-%m-%d %H:%M UTC}) ==")
    if test_mode:
        print("mode: TEST (Buffer API is mocked - nothing reaches LinkedIn)")
    elif dry_run:
        print("mode: DRY RUN (nothing will be published)")

    candidates = fetch_all(config, now)
    story, runners_up = select_story(candidates, config, state_path, now)

    print(f"selected: {story['title']!r} [{story['source']}] score={story['score']}")
    for rank, alt in enumerate(runners_up, start=2):
        print(f"  #{rank} score={alt['score']:7.2f} {alt['title'][:70]}")

    text = compose(story, config, now)
    print("-- post text " + "-" * 45)
    print(text)
    print("-" * 57)

    if dry_run:
        print("dry run complete - state not modified")
        return 0

    transport = None
    if test_mode:
        transport = MockBufferTransport()
        api_key = os.environ.get("BUFFER_API_KEY", "").strip() or "mock_api_key"
        channel_id = (
            os.environ.get("BUFFER_CHANNEL_ID", "").strip() or "mock_linkedin_channel"
        )
        print(f"using mock Buffer channel: {channel_id}")
    else:
        api_key = os.environ.get("BUFFER_API_KEY", "").strip()
        channel_id = os.environ.get("BUFFER_CHANNEL_ID", "").strip()
        if not api_key or not channel_id:
            sys.exit("error: BUFFER_API_KEY and BUFFER_CHANNEL_ID must be set to publish")

    post = create_post(api_key, channel_id, text, transport=transport)
    label = "SIMULATED publish to Buffer" if test_mode else "published to Buffer"
    print(f"{label}: id={post.get('id')} dueAt={post.get('dueAt')}")

    save_state(
        state_path,
        {
            "posted_at": now.isoformat(timespec="seconds"),
            "id": story["id"],
            "title": story["title"],
            "url": story["url"],
            "norm_url": normalize_url(story["url"]),
            "source": story["source"],
            "score": story["score"],
            "buffer_post_id": post.get("id"),
            "text_length": len(text),
            "simulated": test_mode,
        },
    )
    print(f"state updated: {state_path}")
    if test_mode:
        print("test complete - re-run to see dedupe skip this story")
    return 0


if __name__ == "__main__":
    sys.exit(main())
