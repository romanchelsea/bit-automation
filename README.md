# bitbrowser-xhs-playwright

Python helpers for driving **BitBrowser** (local API on `127.0.0.1:54345`) with **Playwright** over **CDP** (`connect_over_cdp`), plus scripts for **小红书创作服务平台** (`creator.xiaohongshu.com`) long-article flows.

## Requirements

- **Python 3.10+**
- **BitBrowser** running with the local API enabled (see [BitBrowser API docs](https://doc2.bitbrowser.cn/))
- A Bit profile **already logged in** to the creator site (cookies stay in the profile)

## Clone and virtual environment

Use a **new venv on each machine** (do not copy `venv/` from another computer).

**macOS / Linux**

```bash
git clone <your-repo-url>
cd <cloned-repo-folder>

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

If you only **attach to Bit** via `connect_over_cdp`, you usually **do not** need Playwright’s bundled Chromium.

If you use Playwright to **launch** its own browsers elsewhere:

```bash
playwright install chromium
```

## Repository structure

```
bit-xhs-scripts/
├── bit_api.py                    # BitBrowser API utility helpers
├── xhs_post_long_article.py      # Main: automated long-article posting flow
├── pyproject.toml
├── README.md
├── tests/
│   ├── bit_playwright.py         # Smoke test: CDP connection verification
│   └── resources/
│       └── sample_xhs_article.txt # Sample article content for testing
└── debug/
    └── xhs_playwright_inspector.py # Debug tool: interactive page inspector
```

## Scripts (usage)

| File | Purpose |
|------|--------|
| `xhs_post_long_article.py` | Automated 小红书长文 posting flow with human-like behavior; accepts `--title` / `--body` or `--body-file`; `--draft` (暂存离开) or publish (发布); optional `--keep-browser-open` after publish for debugging |
| `bit_api.py` | BitBrowser HTTP API helpers (`openBrowser`, `closeBrowser`, …) — imported by scripts |
| `tests/bit_playwright.py` | Smoke test: minimal CDP connection verification |
| `debug/xhs_playwright_inspector.py` | Debug tool: `PWDEBUG=1` + `page.pause()` — Inspector on the Bit tab |
| `tests/resources/sample_xhs_article.txt` | Sample article content for testing and reference |

Example commands:

```bash
# Main workflow: save as draft
python xhs_post_long_article.py --draft --title "标题" --body-file tests/resources/sample_xhs_article.txt

# Main workflow: publish directly
python xhs_post_long_article.py --title "标题" --body "文章内容"

# Smoke test: verify CDP connection
python tests/bit_playwright.py

# Debug: inspect with interactive Inspector
PWDEBUG=1 python debug/xhs_playwright_inspector.py
```

Set **browser window IDs** and URLs in the scripts to match your Bit profile and environment.

## xhs_post_long_article.py: Human-like automation

The script automates the 小红书 long-article creation flow with human-like behavior to avoid detection:

### Typing behavior
- **Character-by-character typing**: Title and body text are typed naturally, not pasted instantly
- **Randomized delays**: Each character has a delay sampled from a normal distribution
  - Mean delay: 50ms per character
  - Standard deviation: 20ms (creates natural variance)
  - Minimum delay: 10ms

### Click behavior
- **Random inter-click delays**: 1–3 seconds between clicks
- **Clickability checks**: Verifies element is visible and enabled before clicking
- **Human-like pauses**: Longer waits at key operations (see timing below)

### Operation timing
The script includes automatic waits at critical operations:
- **一键排版 (Auto-format)**: 30 seconds for formatting to complete
- **下一步 (Next)**: 10 seconds for page transition
- **暂存离开/发布 (Save/Publish)**: 10 seconds for action to complete

### Extensibility: Styling and metadata
The script includes TODO placeholders for future enhancements:

**`_apply_styling_and_templates(page)`** — called before "下一步"
- Choose layout templates
- Set background colors/images
- Apply text formatting

**`_set_post_metadata(page)`** — called before "暂存离开"/"发布"
- Add tags (话题)
- Tag users (@mentions)
- Set post visibility (public/private/followers only)
- Schedule post (timer)
- Pick cover image
- Add location info
- Set content rating

Currently these functions are no-ops but can be implemented incrementally without changing the main flow.

## Cursor skill

Agent guidance for the long-article workflow lives in `.cursor/skills/xhs-creator-long-article/SKILL.md` (optional for non-Cursor users).
