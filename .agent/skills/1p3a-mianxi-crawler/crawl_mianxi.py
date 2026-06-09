"""
Crawl 面经 (interview experience) posts from 1point3acres.com/bbs
via BitBrowser + Playwright over CDP.

The BitBrowser profile must already be logged in to 1point3acres.

Usage:
  python crawl_mianxi.py [options]

Options:
  --company NAME     Company name to search (e.g. "netflix", "google")
  --year YEAR        Hiring year (e.g. 2025; default: 2026)
  --job-category N   Job category value (default: 1 = 码农类General)
  --job-type N       Job type value (default: 1 = 全职)
  --fresh N          应届or在职跳槽 value (default: 2 = 在职跳槽)
  --browser-id ID    BitBrowser window ID (default: f46cbc45596240c0a8b3354cc96def49)
  --output FILE      Save results as JSON; also used as cache key (default: auto-named from filters)
  --force            Ignore cache and re-crawl even if output file exists
  --keep-open        Leave browser open after script finishes

Filter value reference:
  jobyear (招工年度):   16=2026, 15=2025, 14=2024, 13=2023 ...
  jobcategory:          1=码农类General, 7=分析|数据科学类, 8=PM类, 12=MachineLearningEng
  jobtype (工作类别):   1=全职, 2=实习, 3=合同工
  fresh (应届/在职):    1=应届毕业生, 2=在职跳槽, 3=其他
  interviewresult:      1=Pass, 2=Fail, 4=WaitList
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from bit_api import openBrowser, closeBrowser
from playwright.async_api import async_playwright

BBS_URL = "https://www.1point3acres.com/bbs/forum-145-1.html"
DEFAULT_BROWSER_ID = "f46cbc45596240c0a8b3354cc96def49"
CACHE_DIR = Path(__file__).parent / "cache"

# Map year text -> option value (from DOM inspection 2026-06-08)
YEAR_VALUE_MAP = {
    "2026": "16", "2025": "15", "2024": "14", "2023": "13",
    "2022": "12", "2021": "11", "2020": "10", "2019": "9",
}


async def _set_select(page, select_id: str, value: str) -> None:
    await page.select_option(f"#{select_id}", value=value)
    await page.wait_for_timeout(300)


async def _set_company(page, company: str) -> None:
    """Type company name into autocomplete, wait for suggestions, click first match."""
    autocomplete = page.locator("#autocomplete-0-input")
    await autocomplete.click()
    await autocomplete.fill(company)
    await page.wait_for_timeout(1500)

    # Click first autocomplete item if it appeared; otherwise leave typed value as-is
    first_item = page.locator(".aa-Item").first
    if await first_item.count() > 0:
        await first_item.click()
        await page.wait_for_timeout(500)


async def _submit_filters(page) -> None:
    # Must target the named 搜索 button, not the autocomplete submit button.
    # Use expect_navigation so Playwright tracks the POST redirect as a navigation event.
    async with page.expect_navigation(wait_until="domcontentloaded", timeout=30000):
        await page.click('button[name="searchsortsubmit"]')


async def _get_page_urls(page) -> list[str]:
    """Return hrefs for all pages from the .pg widget (page 1 URL is current page.url).

    Builds a deduplicated list ordered by page number.
    Returns a single-element list (current URL) if there is no pagination.
    """
    return await page.evaluate("""() => {
        const pg = document.querySelector('.pg');
        if (!pg) return [location.href];

        const byPage = {1: location.href};
        for (const a of pg.querySelectorAll('a[href]')) {
            const m = a.href.match(/[?&]page=(\\d+)/);
            if (m) {
                const n = parseInt(m[1], 10);
                if (!(n in byPage)) byPage[n] = a.href;
            }
        }
        // Sort by page number and return URLs in order
        return Object.keys(byPage)
            .map(Number)
            .sort((a, b) => a - b)
            .map(n => byPage[n]);
    }""")


async def _extract_posts(page) -> list[dict]:
    """Extract post list from the results page.

    Thread rows are tbody[id^="normalthread_"] elements (not tr).
    Each tbody contains one tr with title, author, time, replies.
    The subtitle span contains structured metadata: category, type, company, result.
    """
    posts = await page.evaluate("""() => {
        const bodies = document.querySelectorAll(
            '#threadlisttableid tbody[id^="normalthread_"], #threadlisttableid tbody[id^="stickthread_"]'
        );
        return Array.from(bodies).map(tb => {
            const titleEl = tb.querySelector('a.xst, a.s.xst');
            const subtitleEl = tb.querySelector('th.common > span');
            const byTds = tb.querySelectorAll('td.by');
            const authorEl = byTds[0]?.querySelector('cite');
            const timeEl = byTds[0]?.querySelector('em span');
            const repliesEl = tb.querySelector('td.num a');
            const tid = tb.id.replace('normalthread_', '').replace('stickthread_', '');
            return {
                title: titleEl ? titleEl.textContent.trim() : '',
                url: titleEl ? titleEl.href : '',
                tid: tid,
                metadata: subtitleEl ? subtitleEl.textContent.trim() : '',
                author: authorEl ? authorEl.textContent.trim() : '',
                time: timeEl ? timeEl.textContent.trim() : '',
                replies: repliesEl ? repliesEl.textContent.trim() : '',
            };
        }).filter(p => p.title);
    }""")
    return posts


def _cache_path(args: argparse.Namespace) -> Path:
    """Return the cache file path for this set of filter args."""
    if args.output:
        return Path(args.output)
    company_slug = args.company.lower().replace(" ", "_") or "any"
    name = f"mianxi_{company_slug}_y{args.year}_cat{args.job_category}_type{args.job_type}_fresh{args.fresh}.json"
    CACHE_DIR.mkdir(exist_ok=True)
    return CACHE_DIR / name


async def run(args: argparse.Namespace) -> list[dict]:
    cache = _cache_path(args)
    if cache.exists() and not args.force:
        posts = json.loads(cache.read_text(encoding="utf-8"))
        print(f"Cache hit: loaded {len(posts)} posts from {cache}")
        return posts

    res = openBrowser(args.browser_id)
    data = res.get("data") or {}
    ws = data.get("ws")
    if not ws:
        raise RuntimeError(f"openBrowser missing ws: {res}")

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(ws)
        context = browser.contexts[0]
        page = await context.new_page()

        print(f"Navigating to BBS 面经 page...")
        await page.goto(BBS_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)

        # Apply filters
        if args.year:
            val = YEAR_VALUE_MAP.get(str(args.year), str(args.year))
            print(f"Setting year: {args.year} → value={val}")
            await _set_select(page, "jobyear", val)

        if args.job_category:
            print(f"Setting job category: {args.job_category}")
            await _set_select(page, "jobcategory", str(args.job_category))

        if args.job_type:
            print(f"Setting job type: {args.job_type}")
            await _set_select(page, "jobtype", str(args.job_type))

        if args.fresh:
            print(f"Setting fresh/experienced: {args.fresh}")
            await _set_select(page, "fresh", str(args.fresh))

        if args.company:
            print(f"Setting company: {args.company}")
            await _set_company(page, args.company)

        print("Submitting filters...")
        await _submit_filters(page)
        await page.wait_for_timeout(2000)

        all_page_urls = await _get_page_urls(page)
        page_urls = all_page_urls if args.max_pages == 0 else all_page_urls[:args.max_pages]
        print(f"Total pages: {len(all_page_urls)} (crawling {len(page_urls)})")

        posts: list[dict] = []
        for pg_num, url in enumerate(page_urls, 1):
            if pg_num > 1:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)
            page_posts = await _extract_posts(page)
            print(f"  Page {pg_num}/{len(page_urls)}: {len(page_posts)} posts")
            posts.extend(page_posts)

        print(f"Total posts: {len(posts)}")
        for i, post in enumerate(posts[:10], 1):
            print(f"  {i:2d}. {post['title'][:60]}  [{post['time']}]")

        cache.write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved {len(posts)} posts to {cache}")

        if not args.keep_open:
            await page.close()
            await browser.close()
            closeBrowser(args.browser_id)
        else:
            await browser.close()
            print("Playwright disconnected; Bit window left open.")

        return posts


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Crawl 1point3acres 面经 via BitBrowser + Playwright.")
    p.add_argument("--company", default="", help="Company name (e.g. netflix)")
    p.add_argument("--year", default="2026", help="Hiring year (default: 2026)")
    p.add_argument("--job-category", default="1", dest="job_category",
                   help="Job category value (default: 1=码农类General)")
    p.add_argument("--job-type", default="1", dest="job_type",
                   help="Job type value (default: 1=全职)")
    p.add_argument("--fresh", default="2",
                   help="应届/在职 value (default: 2=在职跳槽)")
    p.add_argument("--browser-id", default=DEFAULT_BROWSER_ID, dest="browser_id",
                   help="BitBrowser window ID")
    p.add_argument("--output", default="", help="Override cache file path (default: auto-named in cache/)")
    p.add_argument("--max-pages", type=int, default=10, dest="max_pages",
                   help="Max pages to crawl (default: 10; use 0 for unlimited)")
    p.add_argument("--force", action="store_true", help="Re-crawl even if cache exists")
    p.add_argument("--keep-open", action="store_true", dest="keep_open",
                   help="Leave Bit browser open after script finishes")
    return p.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args(sys.argv[1:])
    asyncio.run(run(args))
