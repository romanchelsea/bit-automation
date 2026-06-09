---
name: xhs-creator-long-article
description: Automates long-form 小红书创作服务平台 posts using Playwright over BitBrowser CDP and xhs_recording.py (title/body CLI, --draft for 暂存离开 or default flow clicks 发布; optional --keep-browser-open after 发布 for debugging). Use when automating creator.xiaohongshu.com, 写长文, BitBrowser, connect_over_cdp, sample_xhs_article.txt, or 一键排版 flows.
---

# Xiaohongshu creator: long article via BitBrowser + Playwright

## When this applies

- Target is **PC 创作服务平台** (`creator.xiaohongshu.com`), not the mobile app.
- **Login and cookies** live in a **BitBrowser profile**; automation must **not** log in again in code—reuse that profile via CDP.
- Stack matches this repo: **`bit_api`** (local Bit API) + **`playwright.async_api`** + **`connect_over_cdp`**.
- **Implemented script:** **`xhs_recording.py`** — **`--title`** and **`--body`** or **`--body-file`**; **`--draft`** clicks **暂存离开** (disconnect CDP, Bit stays open); without **`--draft`**, clicks **发布** then **`closeBrowser`** unless **`--keep-browser-open`** (debug: disconnect CDP only). Sample body: **`sample_xhs_article.txt`**.

## This repository: reference implementation

- **`xhs_recording.py`** — end-to-end long-article flow (recorded locators + Bit CDP wiring). **Title and body are CLI inputs**, not hardcoded.
- **`xhs_playwright_inspector.py`** — `connect_over_cdp` + `page.pause()` for **Playwright Inspector** on the Bit tab (locator discovery; not the main publish driver).
- **`bit_playwright.py`** — minimal CDP smoke test; same **`BROWSER_ID`** as below.

## Default Bit profile

- **`browser_id` / `BROWSER_ID`:** `a290134f89cd4d40b7521657919f8366` (keep in sync with `bit_playwright.py` if the Bit window is recreated).
- That profile is **already logged in** to 创作服务平台; automation uses **`browser.contexts[0]`** for cookies. Do not add a login flow unless the user asks or the session expired.

## Setup

All skills share a single venv managed from the **repo root** (`bit-automation/`). `bit_api` is installed as an editable package so any skill can import it directly.

```bash
# from repo root
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate.bat
pip install -e .
```

Run scripts from this skill's directory with the venv active — `import bit_api` will resolve to the root `bit_api.py`.

## How to run `xhs_recording.py`

BitBrowser running, local API up, venv active:

```bash
python xhs_recording.py --title "文章标题" --body "第一段

第二段"
```

Long body from file (UTF-8):

```bash
python xhs_recording.py --title "文章标题" --body-file ./article.txt
```

Draft — after **下一步**, click **暂存离开** (disconnect CDP, **do not** call **`closeBrowser`**; Bit stays open):

```bash
python xhs_recording.py --draft --title "春日下午茶：窗边与慢生活（示例）" --body-file sample_xhs_article.txt
```

Publish — click **发布** after **下一步**:

```bash
python xhs_recording.py --title "文章标题" --body-file ./article.txt
```

Optional — after **发布**, keep Bit open for debugging (**`--keep-browser-open`**, no **`closeBrowser`**):

```bash
python xhs_recording.py --title "文章标题" --body-file ./article.txt --keep-browser-open
```

If the UI changes, re-record or adjust locators in **`xhs_recording.py`** (Inspector on Bit).

## Known long-article flow (verified pattern in `xhs_recording.py`)

Order of operations mirrors the recorded creator UI:

1. **`openBrowser` → `connect_over_cdp(ws)` → `browser.contexts[0].new_page()`**
2. **`goto`** publish hub: `https://creator.xiaohongshu.com/publish/publish?source=official`
3. Click **写长文** → **新的创作**
4. Fill **标题** (`get_by_role("textbox", name="输入标题")`)
5. Fill **正文** in **`.tiptap`** (after focusing `.rich-editor-content` / paragraph)
6. **一键排版** → **下一步**
7. **`--draft`:** click **暂存离开** → disconnect CDP; Bit window stays open.
8. **Else:** click **发布** → if **`--keep-browser-open`**, **`browser.close()`** only (debug); else **`page.close`**, **`browser.close`**, **`closeBrowser(BROWSER_ID)`**.

## Connection pattern (required)

1. `res = openBrowser(browser_id)` — Bit opens the profile window.
2. `ws = res["data"]["ws"]` — WebSocket URL for CDP.
3. `browser = await playwright.chromium.connect_over_cdp(ws)`.
4. `context = browser.contexts[0]` — session with saved 小红书 cookies.
5. `page = await context.new_page()` (or reuse an existing page if needed).

**Cleanup:** `await page.close()`, `await browser.close()` (disconnects Playwright from CDP; **does not** replace the need to **`closeBrowser(browser_id)`** when you want the Bit window closed—match `xhs_recording.py`).

## Creator URLs (hints)

- Publish hub: `https://creator.xiaohongshu.com/publish/publish?source=official`
- Home: `https://creator.xiaohongshu.com/new/home`
- Note manager: `https://creator.xiaohongshu.com/new/note-manager`

## UI fragility and selector strategy

- **Do not** copy long CSS paths from random blogs; **verify** against the current DOM.
- Prefer **`get_by_role`**, **`get_by_text`**, **`get_by_placeholder`**; recorded **`.tiptap`** / **`.rich-editor-content`** may change with site updates.
- **Inspector on Bit:** `PWDEBUG=1 python xhs_playwright_inspector.py` — see below.

## Playwright Inspector on Bit (not `playwright codegen` alone)

The CLI **`playwright codegen`** launches **Playwright’s Chromium**, not Bit.

To record or **Pick locator** on the **Bit** session:

1. `openBrowser` → **`connect_over_cdp(ws)`**
2. Navigate, then **`await page.pause()`** with **`PWDEBUG=1`**
3. Run **`PWDEBUG=1 python xhs_playwright_inspector.py`** (optional URL argument)

## Async hygiene

- Prefer **`await page.wait_for_timeout(ms)`** or **`await page.wait_for_selector(...)`** instead of **`time.sleep`** inside `async def` flows.

## Error handling

- **`openBrowser` fails:** Bit not running or invalid `browser_id`.
- **`connect_over_cdp` fails:** window did not open or **`ws`** missing in response.
- **Login page appears:** wrong profile or expired session—re-login in that Bit window.

## How to use this skill

A **skill** guides the **agent**; you **do not** execute `SKILL.md`. **@**‑mention **`xhs-creator-long-article`** or describe the task so the agent loads this file.

When the user **wants to publish or change** the long-article automation: prefer editing **`xhs_recording.py`**, keep **`BROWSER_ID`** consistent, pass **`--title`** / **`--body`** or **`--body-file`**, and adjust the tail of the flow if **发布** or **暂存离开** behavior needs to change.
