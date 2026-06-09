---
name: 1p3a-mianjing-crawler
description: Crawl, classify and report on 面经 (interview experience posts) from 1point3acres.com/bbs forum-145 via BitBrowser + Playwright over CDP. Filters by company, year, job category, job type, 应届/在职跳槽. Classifies questions (behavioral/coding/system_design) via Claude Haiku. Use when crawling 一亩三分地 面经, 1point3acres BBS interview posts, running crawl_mianjing.py, or parse_mianjing.py.
---

# 1point3acres 面经 crawler + classifier

Two-script pipeline:
1. **`crawl_mianjing.py`** — navigate to forum-145-1.html, apply filters, extract the post list → cached JSON
2. **`parse_mianjing.py`** — crawl each post's content, classify questions via Claude Haiku, generate a markdown report

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

## Agent decision path

When a user says "帮我分析 X 公司的面经" or "crawl and parse Y interview posts":

1. **Extract parameters** from the user request:
   - `company` — company name (e.g. `netflix`, `google`, `meta`)
   - `year` — default `2025` (most data); use `2026` only if user says "recent" or "latest"
   - `job-category` — default `1` (码农); change for data science (`7`), PM (`8`), ML (`12`)
   - `job-type` — default `1` (全职); `2` for 实习
   - `fresh` — default `2` (在职跳槽); `1` for 应届

2. **Check if cache already exists** before crawling:
   ```bash
   ls .agent/skills/1p3a-mianjing-crawler/cache/mianjing_<company>_y<year>_cat<cat>_type<type>_fresh<fresh>.json
   ```
   If file exists → skip Step 1, go directly to Step 2 (parse).

3. **Step 1 — Crawl** (only if no cache):
   ```bash
   python .agent/skills/1p3a-mianjing-crawler/crawl_mianjing.py \
     --company <company> --year <year> \
     --job-category <cat> --job-type <type> --fresh <fresh>
   ```
   Output: `cache/mianjing_<company>_y<year>_cat<cat>_type<type>_fresh<fresh>.json`

4. **Step 2 — Parse** (auto-detects the cache from Step 1):
   ```bash
   ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
   python .agent/skills/1p3a-mianjing-crawler/parse_mianjing.py \
     --posts .agent/skills/1p3a-mianjing-crawler/cache/mianjing_<company>_y<year>_cat<cat>_type<type>_fresh<fresh>.json
   ```
   Output: `report_mianjing_<company>_y<year>_cat<cat>_type<type>_fresh<fresh>.md`

5. **Return the report path** to the user and show a summary (result stats + top questions per category).

---

## Run (agent path)

From repo root with venv active:

```bash
python .agent/skills/1p3a-mianjing-crawler/crawl_mianjing.py \
  --company netflix \
  --year 2025 \
  --job-category 1 \
  --job-type 1 \
  --fresh 2
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

## Step 2: Parse and classify (parse_mianjing.py)

Requires `ANTHROPIC_API_KEY` env var. Reads the cached post list, crawls each thread page, classifies questions via Claude Haiku, and writes a markdown report.

```bash
# Full pipeline — auto-detects latest posts cache
ANTHROPIC_API_KEY=sk-ant-... python .agent/skills/1p3a-mianjing-crawler/parse_mianjing.py

# Explicit posts file, limit to first 20
ANTHROPIC_API_KEY=sk-ant-... python .agent/skills/1p3a-mianjing-crawler/parse_mianjing.py \
  --posts .agent/skills/1p3a-mianjing-crawler/cache/mianjing_netflix_y2025_cat1_type1_fresh2.json \
  --max-posts 20

# Force re-parse cached content (skip browser)
ANTHROPIC_API_KEY=sk-ant-... python .agent/skills/1p3a-mianjing-crawler/parse_mianjing.py --force-parse
```

Options:

| Flag | Default | Notes |
|------|---------|-------|
| `--posts` | _(auto)_ | Posts list JSON from `crawl_mianjing.py`; auto-detects latest in `cache/` |
| `--browser-id` | `f46cbc45596240c0a8b3354cc96def49` | BitBrowser window ID |
| `--max-posts` | `0` (all) | Limit number of posts to process |
| `--force-crawl` | off | Re-crawl post content even if `cache/posts/<tid>.json` exists |
| `--force-parse` | off | Re-classify even if `cache/parsed/<tid>.json` exists |
| `--keep-open` | off | Leave Bit window open after crawling |
| `--report` | _(auto)_ | Output report path; defaults to `report_<posts_stem>.md` |

Cache layout:
- `cache/posts/<tid>.json` — raw post content
- `cache/parsed/<tid>.json` — classified questions per post
- Report output at repo root (gitignored via `results.json` pattern is separate; report files are not gitignored by default)

Classification categories: `behavioral`, `coding`, `system_design`. Model: `claude-haiku-4-5`.

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
