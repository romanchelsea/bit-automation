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
    └── xhs-creator-long-article/          # 小红书 long-article skill
        ├── SKILL.md                        # Agent guidance
        ├── xhs_post_long_article.py        # Main automation script
        ├── tests/
        │   ├── bit_playwright.py           # Smoke test: CDP connection
        │   └── resources/
        │       └── sample_xhs_article.txt
        └── debug/
            └── xhs_playwright_inspector.py # Interactive page inspector
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

### Coming soon

- **1point3acres BBS** — thread crawling and posting automation
- Additional platforms driven by BitBrowser + LLM

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
