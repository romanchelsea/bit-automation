"""
Draft a sample long article on 小红书创作服务平台 via BitBrowser + Playwright.
Uses logged-in cookies from the Bit profile. Does NOT click 发布 — draft stays in the editor.

By default the Bit window stays open and the tab is not closed so you can review the draft.
Set CLOSE_BIT_WHEN_DONE=1 to close the browser profile when the script exits.
"""

from __future__ import annotations

import asyncio
import os

from bit_api import closeBrowser, openBrowser
from playwright.async_api import Page, async_playwright

BROWSER_ID = "a290134f89cd4d40b7521657919f8366"

# Fake sample content (not real; replace anytime)
FAKE_TITLE = "示例长文标题（自动化草稿·勿发）"
FAKE_BODY = """这是一段用于测试自动化草稿功能的示例正文，并非真实发布内容。

第二段：可以在这里替换为你的真实文章。本脚本只负责填入标题与正文，不会点击发布按钮。

—— 草稿结束 ——"""

CLOSE_BIT_WHEN_DONE = os.environ.get("CLOSE_BIT_WHEN_DONE", "").strip() in ("1", "true", "yes")


async def _try_click_long_article_entry(page: Page) -> None:
    """If the publish hub shows 写长文, open it."""
    for name in ("写长文", "长文"):
        btn = page.get_by_text(name, exact=True)
        try:
            await btn.first.wait_for(state="visible", timeout=4000)
            await btn.first.click()
            await page.wait_for_load_state("domcontentloaded")
            return
        except Exception:
            continue


async def _fill_title(page: Page, title: str) -> bool:
    candidates = [
        page.get_by_placeholder("添加标题"),
        page.get_by_placeholder("填写标题"),
        page.get_by_placeholder("输入标题"),
        page.get_by_placeholder("标题"),
        page.locator('input[placeholder*="标题"]'),
        page.locator('textarea[placeholder*="标题"]'),
        page.locator('input[type="text"]').first,
    ]
    for loc in candidates:
        try:
            target = loc.first
            await target.wait_for(state="visible", timeout=2500)
            await target.click()
            await target.fill(title)
            return True
        except Exception:
            continue
    return False


async def _fill_body(page: Page, body: str) -> bool:
    # Prefer main contenteditable (often title is a separate input; body is larger editor)
    try:
        frames = page.frames
        for frame in frames:
            for sel in ('[contenteditable="true"]', "div.ProseMirror", "article [contenteditable]"):
                loc = frame.locator(sel)
                n = await loc.count()
                if n == 0:
                    continue
                # Pick last visible block editor if multiple (title sometimes contenteditable too)
                for i in range(min(n, 8)):
                    el = loc.nth(i)
                    try:
                        await el.wait_for(state="visible", timeout=2000)
                        await el.click()
                        await el.fill(body)
                        return True
                    except Exception:
                        continue
    except Exception:
        pass

    for sel in ('[contenteditable="true"]', "div.ProseMirror"):
        loc = page.locator(sel)
        try:
            n = await loc.count()
            if n == 0:
                continue
            el = loc.last
            await el.wait_for(state="visible", timeout=4000)
            await el.click()
            await el.fill(body)
            return True
        except Exception:
            continue
    return False


async def run() -> None:
    res = openBrowser(BROWSER_ID)
    data = res.get("data") or {}
    ws = data.get("ws")
    if not ws:
        raise RuntimeError(f"openBrowser missing ws: {res}")

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(ws)
        context = browser.contexts[0]
        page = await context.new_page()

        await page.goto(
            "https://creator.xiaohongshu.com/publish/publish?source=official",
            wait_until="domcontentloaded",
        )
        await _try_click_long_article_entry(page)

        ok_title = await _fill_title(page, FAKE_TITLE)
        ok_body = await _fill_body(page, FAKE_BODY)

        if not ok_title:
            print("WARN: Could not find title field; adjust locators in _fill_title().")
        if not ok_body:
            print("WARN: Could not find body editor; adjust locators in _fill_body().")

        print("Draft prepared (not published). Title/body fill:", ok_title, ok_body)
        print("Do not click 发布 in this script — draft is left in the editor.")

        if CLOSE_BIT_WHEN_DONE:
            await page.close()
            closeBrowser(BROWSER_ID)
            print("CLOSE_BIT_WHEN_DONE set: page closed and Bit profile closed.")
        else:
            print(
                "Playwright will disconnect; Bit window stays open for you to review the draft. "
                "Close the profile in Bit manually when finished."
            )


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
