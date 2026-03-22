"""
Open Playwright Inspector against the BitBrowser window (CDP), so recording / Pick locator
target 小红书 in Bit — not Playwright's bundled Chrome.

The CLI `playwright codegen` always launches Playwright's own browser; it cannot attach to Bit.
Official pattern: connect with `connect_over_cdp`, then `page.pause()` (needs PWDEBUG=1).

Usage (venv active, Bit local API running):

  PWDEBUG=1 python xhs_playwright_inspector.py

Optional start URL:

  PWDEBUG=1 python xhs_playwright_inspector.py "https://creator.xiaohongshu.com/new/home"

In the Inspector window: use Record and Pick locator; interactions use the Bit browser tab.
Resume or close the Inspector when finished; Ctrl+C in the terminal stops the script.
"""

from __future__ import annotations

import asyncio
import os
import sys

# Inspector / pause() expects debug mode (set before Playwright starts if possible).
os.environ.setdefault("PWDEBUG", "1")

from bit_api import openBrowser
from playwright.async_api import async_playwright

BROWSER_ID = "a290134f89cd4d40b7521657919f8366"
DEFAULT_URL = "https://creator.xiaohongshu.com/publish/publish?source=official"


async def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL

    res = openBrowser(BROWSER_ID)
    data = res.get("data") or {}
    ws = data.get("ws")
    if not ws:
        raise RuntimeError(f"openBrowser missing ws: {res}")

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(ws)
        context = browser.contexts[0]
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded")
        print("Bit window + CDP connected. Playwright Inspector should open — use Record / Pick locator.")
        print("If Inspector did not open, run with: PWDEBUG=1 python xhs_playwright_inspector.py")
        await page.pause()


if __name__ == "__main__":
    asyncio.run(main())
