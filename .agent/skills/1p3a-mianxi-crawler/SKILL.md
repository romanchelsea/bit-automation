---
name: 1p3a-mianxi-crawler
description: Crawl 面经 (interview experience posts) from 1point3acres.com/bbs forum-145 via BitBrowser + Playwright over CDP. Filters by company, year, job category, job type, 应届/在职跳槽. Use when crawling 一亩三分地 面经, 1point3acres BBS interview posts, or running crawl_mianxi.py.
---

# 1point3acres 面经 crawler

Connects to a BitBrowser window (already logged in to 1point3acres) via CDP, navigates to the 面经 forum (`forum-145-1.html`), applies filters, and extracts the post list. Driver: `.agent/skills/1p3a-mianxi-crawler/crawl_mianxi.py`.

## Prerequisites

- BitBrowser running with the local API enabled on `127.0.0.1:54345`
- BitBrowser window `f46cbc45596240c0a8b3354cc96def49` already logged in to 1point3acres
- venv installed from repo root (see README)

## Setup

```bash
# from repo root
source .venv/bin/activate
# (if first time) pip install -e .
```

## Run (agent path)

From repo root with venv active:

```bash
python .agent/skills/1p3a-mianxi-crawler/crawl_mianxi.py \
  --company netflix \
  --year 2025 \
  --job-category 1 \
  --job-type 1 \
  --fresh 2 \
  --output results.json
```

Options:

| Flag | Default | Notes |
|------|---------|-------|
| `--company` | _(none)_ | Company name for autocomplete search, e.g. `netflix`, `google`, `meta` |
| `--year` | `2026` | Hiring year. 2025 has most data; 2026 is sparse. |
| `--job-category` | `1` | `1`=码农类General, `7`=数据科学, `8`=PM, `12`=ML Engineering |
| `--job-type` | `1` | `1`=全职, `2`=实习, `3`=合同工 |
| `--fresh` | `2` | `1`=应届毕业生, `2`=在职跳槽, `3`=其他 |
| `--browser-id` | `f46cbc45596240c0a8b3354cc96def49` | BitBrowser window ID |
| `--output` | _(none)_ | Save results to JSON file |
| `--keep-open` | off | Disconnect CDP but leave Bit window open (debug) |

Output JSON fields per post: `title`, `url`, `tid`, `metadata` (category/type/company/result inline text), `author`, `time`, `replies`.

## Gotchas

- **Use `forum-145-1.html`, not `forum.php?fid=259&typeid=189`** — the `fid=259` URL is a different subforum (数据科学面试题目) with no threads after filtering. The correct 面经 board is `fid=145`.
- **`button[name="searchsortsubmit"]` not `button[type=submit]`** — there are two submit buttons on the page: the autocomplete search (which searches the site header) and the 搜索 filter button. Only `name="searchsortsubmit"` submits the filter form.
- **Wait for `networkidle` after submit** — the thread list renders after a JS-driven page load. `domcontentloaded` alone returns before threads appear.
- **Thread rows are `tbody[id^="normalthread_"]`** — not `tr`. Selecting `tr` gives 0 results even when threads are present.
- **Year 2026 returns few results** — most 2026 posts are sparse mid-year. Use `--year 2025` for richer results.
- **`jobyear` is `select` type** — the site marks it as `select` in the form type hints, so `page.select_option()` works directly (no JS event firing needed).

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `openBrowser missing ws` | BitBrowser not running or window ID wrong |
| 0 posts found | Wrong URL (check it's `fid=145`); or networkidle timed out — add 2s sleep |
| Company not filtering | Autocomplete didn't show suggestion; script falls back to typed value in hidden input, which still works |
| Playwright can't connect | Bit window was closed; call `openBrowser` again |
| `Submitting filters...` timeout | `wait_for_load_state` after click misses the POST redirect — use `expect_navigation` wrapping the click (already fixed in driver) |
