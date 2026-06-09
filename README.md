# bit-automation

A collection of **BitBrowser + LLM** powered skills for crawling and automating websites — starting with **小红书 (Xiaohongshu)** and expanding to other platforms like **1point3acres BBS**.

Each skill drives a **BitBrowser** profile (local API on `127.0.0.1:54345`) via **Playwright over CDP**, keeping login sessions and cookies inside the Bit profile so scripts never need to re-authenticate.

## Requirements

- **Python 3.10+**
- **BitBrowser** running with the local API enabled (see [BitBrowser API docs](https://doc2.bitbrowser.cn/))
- A Bit profile **already logged in** to the target site (cookies stay in the profile)

## Clone and virtual environment

Use a **new venv on each machine** (do not copy `venv/` from another computer).

**macOS / Linux**

```bash
git clone git@github.com:romanchelsea/bit-automation.git
cd bit-automation

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
```

**Windows (cmd)**

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -U pip
```

## Install this project

**Editable install** (recommended while developing — code changes apply immediately):

```bash
pip install -e .
```

**One-off install** (copy into the environment):

```bash
pip install .
```

**Optional dev tools** (e.g. Ruff):

```bash
pip install -e ".[dev]"
```

## Playwright browsers

If you only **attach to Bit** via `connect_over_cdp`, you usually **do not** need Playwright's bundled Chromium.

If you use Playwright to **launch** its own browsers elsewhere:

```bash
playwright install chromium
```

## Repository structure

```
bit-automation/
├── bit_api.py                              # Shared: BitBrowser API helpers
├── pyproject.toml
├── README.md
└── .agent/skills/
    ├── xhs-creator-long-article/          # 小红书 long-article skill
    │   ├── SKILL.md
    │   ├── xhs_post_long_article.py
    │   ├── tests/
    │   │   ├── bit_playwright.py
    │   │   └── resources/
    │   │       └── sample_xhs_article.txt
    │   └── debug/
    │       └── xhs_playwright_inspector.py
    └── 1p3a-mianjing-crawler/               # 1point3acres 面经 crawler skill
        ├── SKILL.md
        ├── crawl_mianjing.py                # Crawl post list (filters + pagination)
        ├── parse_mianjing.py                # Fetch per-post content + LLM classify
        ├── env.local                      # API key (gitignored)
        └── cache/                         # Crawl cache (gitignored)
            ├── mianjing_*.json              # Post list cache per filter set
            └── posts/<tid>.json           # Per-post content cache
```

## Skills

### 小红书 (Xiaohongshu) — long article posting

Automates the 小红书创作服务平台 (`creator.xiaohongshu.com`) long-article creation flow with human-like behavior.

```bash
# from the skill directory
cd .agent/skills/xhs-creator-long-article

# Save as draft
python xhs_post_long_article.py --draft --title "标题" --body-file tests/resources/sample_xhs_article.txt

# Publish directly
python xhs_post_long_article.py --title "标题" --body "文章内容"
```

**Options:** `--title`, `--body` or `--body-file`, `--draft` (暂存离开), `--keep-browser-open` (debug)

#### Body text normalization
- Converts Windows/Mac line endings to Unix `\n`
- Decodes shell-escaped newlines (`\\n`, `\\r\\n`) into real newlines
- Collapses multiple consecutive newlines into one
- Strips outer quote wrappers from `--body` values

#### Human-like behavior
- Character-by-character typing with randomized per-keystroke delays (mean 50ms, σ 20ms, min 10ms)
- Random inter-click delays (1–3 seconds)
- Automatic waits at critical UI steps: 一键排版 (30s), 下一步 (10s), 暂存离开/发布 (10s)

#### Planned extensions
- `_apply_styling_and_templates(page)` — layout templates, background, text formatting
- `_set_post_metadata(page)` — tags, @mentions, visibility, schedule, cover image, location

---

### 1point3acres BBS — 面经 crawler

Crawls 面经 (interview experience) posts from [1point3acres.com/bbs](https://www.1point3acres.com/bbs/forum-145-1.html) via BitBrowser + Playwright over CDP, then optionally fetches and classifies post content with Claude.

**Two-stage pipeline:**

| Stage | Script | What it does |
|-------|--------|-------------|
| 1. Crawl list | `crawl_mianjing.py` | Applies filters (company, year, job type), paginates, saves post metadata to `cache/mianjing_*.json` |
| 2. Fetch + classify | `parse_mianjing.py` | Reads each post's full content via Playwright, calls Claude to classify coding/SD/BQ topics, saves to `cache/posts/<tid>.json` |

```bash
cd .agent/skills/1p3a-mianjing-crawler

# Crawl Netflix 2025 面经 list (cached after first run)
python crawl_mianjing.py --company netflix --year 2025

# Fetch post content only (skip LLM classification)
python parse_mianjing.py --crawl-only

# Full pipeline: fetch content + Claude classification
python parse_mianjing.py
```

**Filters:** `--company`, `--year` (2025/2026), `--job-category` (1=码农), `--job-type` (1=全职), `--fresh` (2=在职跳槽), `--max-pages`

**Cache:** both stages cache results to disk; re-runs are instant unless `--force` is passed.

**Reports generated so far** (in repo root):

| File | Contents |
|------|----------|
| `report_mianjing_netflix_y2025_cat1_type1_fresh2.md` | Netflix 2025 面经汇总（58 posts） |
| `report_mianjing_netflix_y2026_cat1_type1_fresh2.md` | Netflix 2026 面经汇总（28 posts） |
| `report_mianjing_netflix_ads_2025_2026.md` / `.pdf` | Ads 组专项汇总（86 posts 全量，含 PDF） |

---

---

## Next steps

### Human-like behavior improvements (both skills)

Both scripts currently have some human-like delays but are detectable as bots at a closer look. Planned improvements:

**`crawl_mianjing.py`** (currently minimal anti-bot measures):

- [ ] Replace all fixed `wait_for_timeout(N)` calls with `jitter(base, ±range)` random intervals
- [ ] Company autocomplete: replace `fill()` (instant paste) with character-by-character typing using gaussian delays
- [ ] Filter selects: add mouse `hover` → pause → `click` sequence instead of direct `select_option`
- [ ] Between pages: add random `mouse.wheel` scroll (simulate reading the page) before navigating
- [ ] Between HTTP navigations: add random pre-navigation pause (0.5–2s) to simulate reading time

**`xhs_post_long_article.py`** (already has per-keystroke jitter and random click delays):

- [ ] `_click_with_delay`: before clicking, first `mouse.move` to a random point near the element, pause briefly, then move to the target and click — avoids teleporting cursor
- [ ] Replace all fixed `asyncio.sleep(30)` / `asyncio.sleep(10)` waits with `±20%` jitter (e.g. `sleep(random.uniform(24, 36))`)

**Shared utility (to extract):**

- [ ] Add a `human.py` helper module with `jitter_sleep(base, pct=0.2)`, `human_move_and_click(page, locator)`, `human_type(locator, text)` — so both skills share the same anti-detection primitives

---

## Shared utilities

| File | Purpose |
|------|---------|
| `bit_api.py` | BitBrowser HTTP API helpers (`openBrowser`, `closeBrowser`, …) — imported by all skills |

Set **browser window IDs** and URLs in each script to match your Bit profile and environment.

## Agent skills

Agent guidance for each workflow lives under `.agent/skills/`. Each skill's `SKILL.md` tells the agent what the skill does, how to run it, and what patterns to follow.

To make skills available to your AI agent tool, symlink this repo's skills directory into the tool's skills folder. The symlink lets the agent discover and load `SKILL.md` files while the actual code stays in this repo.

### Claude Code

```bash
mkdir -p ~/.claude/skills
ln -s /path/to/bit-automation/.agent/skills/xhs-creator-long-article ~/.claude/skills/xhs-creator-long-article
```

### Cursor

```bash
mkdir -p ~/.cursor/skills
ln -s /path/to/bit-automation/.agent/skills/xhs-creator-long-article ~/.cursor/skills/xhs-creator-long-article
```

### OpenAI Codex

```bash
mkdir -p ~/.codex/skills
ln -s /path/to/bit-automation/.agent/skills/xhs-creator-long-article ~/.codex/skills/xhs-creator-long-article
```

Replace `/path/to/bit-automation` with the absolute path to your cloned repo (e.g. `~/projects/bit-automation`). After symlinking, reference a skill by name in your agent prompt (e.g. `@xhs-creator-long-article`) — the agent reads `SKILL.md` for context but does not execute it directly.
