"""
Automated workflow for posting long articles to 小红书创作服务平台 (XHS Creator), wired via BitBrowser + Playwright over CDP.

Uses human-like automation: character-by-character typing, randomized delays, and realistic wait times.

Requires Bit running, local API, and BROWSER_ID profile logged into creator.

Examples:
  python xhs_post_long_article.py --title "我的标题" --body "第一段\\n\\n第二段"
  python xhs_post_long_article.py --title "我的标题" --body-file ./article.txt

Draft (click 暂存离开 and leave Bit open):
  python xhs_post_long_article.py --draft --title "春日下午茶（示例）" --body-file tests/resources/sample_xhs_article.txt

Publish (click 发布):
  python xhs_post_long_article.py --title "我的标题" --body-file ./article.txt

Publish with Bit open for debugging (no closeBrowser):
  python xhs_post_long_article.py --title "我的标题" --body-file ./article.txt --keep-browser-open
"""

from __future__ import annotations

import argparse
import asyncio
import random
import sys
from pathlib import Path

from bit_api import closeBrowser, openBrowser
from playwright.async_api import Playwright, Locator, async_playwright

BROWSER_ID = "a290134f89cd4d40b7521657919f8366"
START_URL = "https://creator.xiaohongshu.com/publish/publish?source=official"


def _load_body(args: argparse.Namespace) -> str:
    if args.body_file is not None:
        return Path(args.body_file).read_text(encoding="utf-8")
    assert args.body is not None
    return args.body


async def _click_with_delay(locator: Locator, delay_min: float = 1.0, delay_max: float = 3.0) -> None:
    """Wait for element to be clickable and click with random delay (human-like).
    
    Args:
        locator: Playwright locator for the element to click
        delay_min: Minimum delay in seconds (default 1.0)
        delay_max: Maximum delay in seconds (default 3.0)
    """
    # Wait for element to be visible
    await locator.wait_for(state="visible", timeout=5000)
    
    # Wait for element to be enabled (clickable)
    await locator.evaluate("el => el.disabled === false || el.disabled === undefined")
    
    # Add random delay (human-like)
    delay = random.uniform(delay_min, delay_max)
    await asyncio.sleep(delay)
    
    # Click
    await locator.click()


async def _type_with_delay(locator: Locator, text: str, mean_delay_ms: int = 50, std_dev_ms: int = 20) -> None:
    """Type text character by character with randomized delays (human-like typing).
    
    Args:
        locator: Playwright locator for the input element
        text: Text to type
        mean_delay_ms: Mean delay in milliseconds between characters (default 50ms)
        std_dev_ms: Standard deviation of delays in milliseconds (default 20ms, creates normal distribution)
    """
    # First clear and focus on the element
    await locator.focus()
    await locator.clear()
    
    # Type each character with randomized delay to mimic human typing variance
    for char in text:
        # Generate random delay from normal distribution for realistic typing speed variation
        delay_ms = max(10, random.gauss(mean_delay_ms, std_dev_ms))  # Ensure minimum 10ms
        await asyncio.sleep(delay_ms / 1000)
        await locator.type(char)


async def _apply_styling_and_templates(page) -> None:
    """Apply templates and styling options before clicking 下一步.
    
    TODO: Implement the following optional steps:
    - Choose layout templates
    - Set background color/image
    - Apply text formatting styles
    
    Args:
        page: Playwright page object
    """
    # Placeholder for future styling implementation
    pass


async def _set_post_metadata(page) -> None:
    """Set post metadata before publishing/drafting.
    
    TODO: Implement the following optional metadata options:
    - Add tags (话题)
    - Tag users (@mentions)
    - Set post visibility (public/private/followers only)
    - Set timer for scheduled posting
    - Pick/set cover image
    - Add location information
    - Set content rating/maturity level
    
    Args:
        page: Playwright page object
    """
    # Placeholder for future metadata implementation
    pass



async def run(
    playwright: Playwright,
    *,
    title: str,
    body: str,
    draft: bool,
    keep_browser_open: bool,
) -> None:
    res = openBrowser(BROWSER_ID)
    data = res.get("data") or {}
    ws = data.get("ws")
    if not ws:
        raise RuntimeError(f"openBrowser missing ws: {res}")

    browser = await playwright.chromium.connect_over_cdp(ws)
    context = browser.contexts[0]
    page = await context.new_page()

    await page.goto(START_URL, wait_until="domcontentloaded")

    await _click_with_delay(page.get_by_text("写长文"))
    await _click_with_delay(page.get_by_role("button", name="新的创作"))
    await _click_with_delay(page.get_by_role("textbox", name="输入标题"))
    await _type_with_delay(page.get_by_role("textbox", name="输入标题"), title)
    await _click_with_delay(page.locator(".rich-editor-content"))
    await _click_with_delay(page.get_by_role("paragraph"))
    await _type_with_delay(page.locator(".tiptap"), body)
    await _click_with_delay(page.get_by_role("button", name="一键排版"))
    await asyncio.sleep(30)  # Wait for formatting to complete
    
    # TODO: Apply styling and templates if needed
    await _apply_styling_and_templates(page)
    
    await _click_with_delay(page.get_by_role("button", name="下一步"))
    await asyncio.sleep(10)  # Wait for page transition
    
    # TODO: Set post metadata (tags, visibility, timer, cover image, etc.)
    await _set_post_metadata(page)

    if draft:
        await _click_with_delay(page.get_by_role("button", name="暂存离开"))
        await asyncio.sleep(10)  # Wait for draft save
        await browser.close()
        print("Draft: clicked 暂存离开. Playwright disconnected; Bit window left open.")
        return

    await _click_with_delay(page.get_by_role("button", name="发布"))
    await asyncio.sleep(10)  # Wait for publish to complete
    if keep_browser_open:
        await browser.close()
        print("Publish: clicked 发布. Playwright disconnected; Bit window left open (debug).")
        return

    await page.close()
    await browser.close()
    closeBrowser(BROWSER_ID)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="小红书长文 via BitBrowser + Playwright.")
    p.add_argument("--title", required=True, help="Article title")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--body", help="Article body (use \\n for newlines in shell)")
    g.add_argument("--body-file", metavar="PATH", help="Read body from UTF-8 file")
    p.add_argument(
        "--draft",
        action="store_true",
        help="After 下一步: click 暂存离开 (save draft), disconnect CDP, leave Bit open.",
    )
    p.add_argument(
        "--keep-browser-open",
        action="store_true",
        help="After 发布: disconnect CDP only; do not closeBrowser (ignored with --draft). For debugging.",
    )
    return p.parse_args(argv)


async def main() -> None:
    args = _parse_args(sys.argv[1:])
    body = _load_body(args)
    async with async_playwright() as playwright:
        await run(
            playwright,
            title=args.title,
            body=body,
            draft=args.draft,
            keep_browser_open=args.keep_browser_open,
        )


if __name__ == "__main__":
    asyncio.run(main())
