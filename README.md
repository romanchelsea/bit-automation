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

## Scripts (overview)

| File | Purpose |
|------|--------|
| `bit_api.py` | BitBrowser HTTP API helpers (`openBrowser`, `closeBrowser`, …) |
| `bit_playwright.py` | Minimal CDP smoke test |
| `xhs_recording.py` | Recorded 小红书长文 flow; `--title` / `--body` or `--body-file`; `--stop-before-publish` |
| `xhs_playwright_inspector.py` | `PWDEBUG=1` + `page.pause()` — Inspector on the Bit tab |
| `xhs_draft_sample.py` | Older draft experiment (generic locators) |

Example:

```bash
python xhs_recording.py --stop-before-publish --title "标题" --body-file sample_xhs_article.txt
```

Set **browser window IDs** and URLs in the scripts to match your Bit profile and environment.

## Cursor skill

Agent guidance for the long-article workflow lives in `.cursor/skills/xhs-creator-long-article/SKILL.md` (optional for non-Cursor users).
