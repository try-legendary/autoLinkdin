# SETUP - step by step

Repo: https://github.com/try-legendary/autoLinkdin

## Part A - One-time setup

### 1. Buffer: connect LinkedIn and get two values

1. Go to [buffer.com](https://buffer.com), sign up / log in (free plan is fine).
2. **Channels -> Connect a channel -> LinkedIn** - authorize your
   **personal profile** (not a Page).
3. Open <https://publish.buffer.com/settings/api> and copy the API key.
4. Find your LinkedIn channel ID:

   ```bash
   cd ~/daily-tech-post
   BUFFER_API_KEY=your_key python3 scripts/buffer_channels.py
   ```

   Copy the ID on the line marked `<-- use this`.

### 2. Add the secrets to GitHub

Repo -> **Settings -> Secrets and variables -> Actions -> New repository secret**:

| Name                | Value                                |
|---------------------|--------------------------------------|
| `BUFFER_API_KEY`    | from step 1.3                        |
| `BUFFER_CHANNEL_ID` | from step 1.4                        |

### 3. Test once

Actions tab -> **Daily tech post** -> **Run workflow**:

- first run with **dry_run checked** - the log shows the chosen story and the
  exact post text, publishes nothing;
- then run with **dry_run unchecked** - a post enters your Buffer queue and is
  published to LinkedIn.

The weekday cron (`0 14 * * 1-5` UTC) runs on its own from then on.

## Part B - What happens every day (automatic)

```
Weekday 14:00 UTC -> GitHub triggers the workflow
                  -> pulls the top tech story (Hacker News + RSS,
                     skipping stories posted in the last 30 days)
                  -> renders the post text from your template
                  -> queues it in Buffer -> Buffer posts it to LinkedIn
                  -> records the story so it is never repeated
```

## Part C - Changing things

| You want to...            | Do this                                                  |
|---------------------------|----------------------------------------------------------|
| Change posting time       | edit `cron` in `.github/workflows/daily-post.yml`        |
| Add / remove news feeds   | edit `sources.rss` in `config.json`                      |
| Change the post wording   | edit `post.templates` in `config.json` (one per weekday) |
| Change hashtags           | edit `post.hashtags` in `config.json`                    |
| Post right now            | Actions -> Run workflow -> dry_run unchecked             |
| Preview without posting   | Actions -> Run workflow -> dry_run checked               |
| Run the whole thing offline | `python3 scripts/run.py --test`                        |

After any edit:

```bash
cd ~/daily-tech-post
git add -A && git commit -m "tweak config" && git push
```

## Part D - Maintenance

- **Check it worked:** Buffer -> your LinkedIn channel shows the queued / sent
  post. Or look at your LinkedIn profile.
- **Buffer <-> LinkedIn disconnects occasionally:** reconnect in Buffer, then
  re-run the workflow from the Actions tab.
- **A run failed:** GitHub emails you. Open the failed run and read the log -
  usually a news source outage or an expired Buffer connection.
- **GitHub pauses cron after 60 days of no repo activity** - the daily state
  commit keeps the repo active, so this normally does not happen. If it ever
  pauses, re-enable it from the Actions tab.
- **Cost:** free - GitHub Actions free tier and the Buffer free plan (check
  buffer.com/pricing for the current queue limits).
