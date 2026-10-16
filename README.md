# daily-tech-post

Automated daily tech post to your **LinkedIn profile**, curated from news
(Hacker News + RSS), written from templates, published through the
[Buffer API](https://developers.buffer.com), scheduled by GitHub Actions.

No dependencies - pure Python standard library.

> First time here? See [SETUP.md](SETUP.md) for the full step-by-step guide.

## How it works

```
GitHub Actions cron (weekdays 14:00 UTC)
  1. fetch    - HN front page + recent popular stories, TechCrunch/Verge/Ars RSS
  2. select   - score by popularity + recency, skip anything in state/posted.json (30 days)
  3. compose  - render config.json template (rotates by weekday)
  4. publish  - Buffer GraphQL createPost -> your LinkedIn channel (queue)
  5. record   - append to state/posted.json, commit back to the repo
```

## One-time setup

### 1. Buffer (publishing layer)

1. Create a free account at [buffer.com](https://buffer.com) and connect your
   LinkedIn profile (Channels -> Connect -> LinkedIn).
2. Get an API key: <https://publish.buffer.com/settings/api>
3. List your channels to find the LinkedIn channel ID:

   ```bash
   BUFFER_API_KEY=your_key python3 scripts/buffer_channels.py
   ```

   Copy the `linkedin` channel id (looks like `1234abcd...`).

### 2. GitHub repository

1. Create a repo and push this directory:

   ```bash
   git init && git add . && git commit -m "Daily tech post pipeline"
   git remote add origin git@github.com:YOU/daily-tech-post.git
   git push -u origin main
   ```

2. Repo -> Settings -> Secrets and variables -> Actions -> New repository secret:

   | Secret              | Value                          |
   |---------------------|--------------------------------|
   | `BUFFER_API_KEY`    | your Buffer API key            |
   | `BUFFER_CHANNEL_ID` | the LinkedIn channel ID above  |

### 3. Test, then let it run

1. Actions tab -> **Daily tech post** -> **Run workflow** -> keep
   **dry_run** checked. The log prints the chosen story and exact post text
   without publishing.
2. Run again with **dry_run** unchecked - the post appears in Buffer's queue
   (next slot in your Buffer schedule) and on LinkedIn afterwards.
3. The weekday cron takes over from there.

## Local usage

```bash
python3 scripts/run.py --dry-run     # fetch, select, compose - publish nothing
python3 scripts/run.py --test        # full run incl. publish, against a mocked Buffer API
python3 scripts/run.py               # full run (needs Buffer env vars)
python3 scripts/buffer_channels.py --mock      # offline demo of channel listing
python3 scripts/buffer_channels.py             # list your real Buffer channels
```

### Test mode (`--test`)

Runs the **entire** pipeline - fetch, select, compose, and publish - but the
Buffer API is replaced by an in-memory fake, so nothing touches your LinkedIn
account and no API key is needed.

```bash
python3 scripts/run.py --test
```

- Prints the exact GraphQL call that would go to Buffer, plus a simulated
  response (`mock_post_...`, `dueAt`).
- Records to `state/posted.test.json` (git-ignored), **not** your real
  `state/posted.json`, so it never affects production dedupe.
- Run it twice: the second run skips the first story (dedupe) and picks the
  next one - proving the record-then-skip loop works.


## Configuration (`config.json`)

- **sources.hackernews** - `min_points`, `max_age_hours`, enable/disable
- **sources.rss** - add/remove feeds; `weight` = relative importance vs HN
- **selection.lookback_days** - how long a posted story stays excluded
- **post.templates** - one template per weekday (`mon`..`sun`) + `default`;
  placeholders: `{title}` `{url}` `{source}` `{detail}` `{hashtags}`
  `{points}` `{comments}` `{hn_url}`
- **post.hashtags** - appended to every post
- **post.max_length** - 3000 (LinkedIn limit)

Schedule lives in `.github/workflows/daily-post.yml` (`cron`, UTC).

## Notes

- **Buffer free plan** includes the API; queue/channel limits apply - see
  Buffer's current plan page if posts ever get rejected.
- If the Buffer <-> LinkedIn connection expires, the workflow fails and
  GitHub emails you. Reconnect in Buffer, then re-run the workflow.
- GitHub `schedule` triggers can fire several minutes late on busy days.
- The state file (`state/posted.json`) must be committed by the workflow
  (`permissions: contents: write` is already set).

## Facebook

Not included: Facebook removed API posting for personal profiles in 2018,
so there is no compliant way to auto-post there (Pages are supported if you
ever create one - Buffer can post to Pages with the same pipeline).
