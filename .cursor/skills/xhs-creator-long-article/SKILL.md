---
name: xhs-creator-long-article
description: Automates long-form 小红书创作服务平台 posts using Playwright over BitBrowser CDP and xhs_recording.py (title/body CLI, optional --stop-before-publish for draft-only). Use when automating creator.xiaohongshu.com, 写长文, BitBrowser, connect_over_cdp, sample_xhs_article.txt, or topic / 一键排版 flows.
---

# Xiaohongshu creator: long article via BitBrowser + Playwright

## When this applies

- Target is **PC 创作服务平台** (`creator.xiaohongshu.com`), not the mobile app.
- **Login and cookies** live in a **BitBrowser profile**; automation must **not** log in again in code—reuse that profile via CDP.
- Stack matches this repo: **`bit_api`** (local Bit API) + **`playwright.async_api`** + **`connect_over_cdp`**.
- **Implemented script:** **`xhs_recording.py`** — **`--title`** and **`--body`** or **`--body-file`**; optional **`--topic-tag`**; **`--stop-before-publish`** stops after **下一步** (no topic / no **发布**, leaves Bit open). Sample body: **`sample_xhs_article.txt`**.

## This repository: reference implementation

- **`xhs_recording.py`** — end-to-end long-article flow (recorded locators + Bit CDP wiring). **Title and body are CLI inputs**, not hardcoded.
- **`xhs_playwright_inspector.py`** — `connect_over_cdp` + `page.pause()` for **Playwright Inspector** on the Bit tab (locator discovery; not the main publish driver).
- **`bit_playwright.py`** — minimal CDP smoke test; same **`BROWSER_ID`** as below.

## Default Bit profile

- **`browser_id` / `BROWSER_ID`:** `a290134f89cd4d40b7521657919f8366` (keep in sync with `bit_playwright.py` if the Bit window is recreated).
- That profile is **already logged in** to 创作服务平台; automation uses **`browser.contexts[0]`** for cookies. Do not add a login flow unless the user asks or the session expired.

## How to run `xhs_recording.py`

BitBrowser running, local API up (`bit_api.py`), venv with **`playwright`** + **`requests`**:

```bash
python xhs_recording.py --title "文章标题" --body "第一段

第二段"
```

Long body from file (UTF-8):

```bash
python xhs_recording.py --title "文章标题" --body-file ./article.txt
```

Draft only — **stop before topic / 发布** (disconnect CDP, **do not** close the Bit tab or call **`closeBrowser`**):

```bash
python xhs_recording.py --stop-before-publish --title "春日下午茶：窗边与慢生活（示例）" --body-file sample_xhs_article.txt
```

Full flow (includes topic click; still no **发布** in script unless you add it):

```bash
python xhs_recording.py --title "文章标题" --body-file ./article.txt --topic-tag "#你的话题"
```

If the UI or topic list changes, re-record or adjust locators in **`xhs_recording.py`** (Inspector on Bit).

## Known long-article flow (verified pattern in `xhs_recording.py`)

Order of operations mirrors the recorded creator UI:

1. **`openBrowser` → `connect_over_cdp(ws)` → `browser.contexts[0].new_page()`**
2. **`goto`** publish hub: `https://creator.xiaohongshu.com/publish/publish?source=official`
3. Click **写长文** → **新的创作**
4. Fill **标题** (`get_by_role("textbox", name="输入标题")`)
5. Fill **正文** in **`.tiptap`** (after focusing `.rich-editor-content` / paragraph)
6. **Select all** in editor, then a **cursor nudge** (`ArrowRight` on a div matching the **first line** of the body — same idea as the original `^Bar$` step; may need tweaks if the DOM splits text differently)
7. **一键排版** → **下一步**
8. **Optional:** click **topic** (default **`#生活美学`**, **`--topic-tag`**) — **skipped** when **`--stop-before-publish`** (draft-only: stop on the step before topic/publish; user finishes in Bit).

**发布:** the script never clicks **发布** unless you add that step. Use **`--stop-before-publish`** to end after **下一步** and leave the Bit window open for manual topic + **发布**.

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

## How to use this skill in Cursor

A **skill** guides the **agent**; you **do not** execute `SKILL.md`. **@**‑mention **`xhs-creator-long-article`** or describe the task so the agent loads this file.

When the user **wants to publish or change** the long-article automation: prefer editing **`xhs_recording.py`**, keep **`BROWSER_ID`** consistent, pass **`--title`** / **`--body`** or **`--body-file`**, and adjust **`--topic-tag`** or the tail of the flow if **发布** is required.
