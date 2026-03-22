"""
Recorded Playwright flow for 小红书创作服务平台, wired to BitBrowser via CDP.

Requires Bit running, local API, and BROWSER_ID profile logged into creator.

Examples:
  python xhs_recording.py --title "我的标题" --body "第一段\\n\\n第二段"
  python xhs_recording.py --title "我的标题" --body-file ./article.txt

Draft only (stop after 下一步, no topic click, no 发布; Bit tab stays open):
  python xhs_recording.py --stop-before-publish --title "春日下午茶（示例）" --body-file sample_xhs_article.txt
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path

from bit_api import closeBrowser, openBrowser
from playwright.async_api import Playwright, async_playwright

BROWSER_ID = "a290134f89cd4d40b7521657919f8366"
START_URL = "https://creator.xiaohongshu.com/publish/publish?source=official"


def _load_body(args: argparse.Namespace) -> str:
    if args.body_file is not None:
        return Path(args.body_file).read_text(encoding="utf-8")
    assert args.body is not None
    return args.body


def _body_anchor_pattern(body: str) -> re.Pattern[str]:
    """Match the first line for the post-fill cursor step (recorded against short sample text)."""
    lines = body.splitlines()
    first = lines[0] if lines else body
    if not first.strip():
        first = body.strip() or " "
    return re.compile("^" + re.escape(first) + "$")


async def run(
    playwright: Playwright,
    *,
    title: str,
    body: str,
    topic_tag: str,
    stop_before_publish: bool,
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

    await page.get_by_text("写长文").click()
    await page.get_by_role("button", name="新的创作").click()
    await page.get_by_role("textbox", name="输入标题").click()
    await page.get_by_role("textbox", name="输入标题").fill(title)
    await page.locator(".rich-editor-content").click()
    await page.get_by_role("paragraph").click()
    await page.locator(".tiptap").fill(body)
    await page.locator(".tiptap").press("ControlOrMeta+a")
    await page.locator("div").filter(has_text=_body_anchor_pattern(body)).nth(2).press("ArrowRight")
    await page.get_by_role("button", name="一键排版").click()
    await page.get_by_role("button", name="下一步").click()

    if stop_before_publish:
        # Do not select topic or click 发布; leave editor flow for manual finish in Bit.
        await browser.close()
        print(
            "Stopped before publish (no topic / no 发布). "
            "Bit window left open — complete topic and 发布 in the browser if needed."
        )
        return

    await page.get_by_text(topic_tag).first.click()

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
        "--topic-tag",
        default="#生活美学",
        help='Topic tag to click before publish (default: "#生活美学"); ignored with --stop-before-publish',
    )
    p.add_argument(
        "--stop-before-publish",
        action="store_true",
        help="After 下一步, stop: no topic click, no 发布; disconnect CDP and leave Bit open.",
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
            topic_tag=args.topic_tag,
            stop_before_publish=args.stop_before_publish,
        )


if __name__ == "__main__":
    asyncio.run(main())
