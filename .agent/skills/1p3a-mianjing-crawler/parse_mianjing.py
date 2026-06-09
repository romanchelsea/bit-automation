"""
Parse and classify 面经 posts from 1point3acres using Claude API (Haiku).

Pipeline:
  1. Load post list from crawl_mianjing.py cache (JSON with tid/url/title)
  2. Crawl each post's content via BitBrowser + Playwright (cached to cache/posts/<tid>.json)
  3. Classify questions into behavioral / coding / system_design via Claude Haiku
     (cached to cache/parsed/<tid>.json)
  4. Aggregate into a summary report

Usage:
  python parse_mianjing.py [options]

Options:
  --posts FILE         Path to posts list JSON from crawl_mianjing.py (default: auto-detect latest in cache/)
  --browser-id ID      BitBrowser window ID
  --max-posts N        Max posts to process (default: 0 = all)
  --force-crawl        Re-crawl post content even if cached
  --force-parse        Re-classify even if cached
  --keep-open          Leave browser open after script finishes
  --report FILE        Output report path (default: report_<company>_<date>.md)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import anthropic
from bit_api import openBrowser, closeBrowser
from playwright.async_api import async_playwright

CACHE_DIR = Path(__file__).parent / "cache"
POSTS_CACHE_DIR = CACHE_DIR / "posts"
PARSED_CACHE_DIR = CACHE_DIR / "parsed"
DEFAULT_BROWSER_ID = "f46cbc45596240c0a8b3354cc96def49"

CLASSIFY_PROMPT = """\
You are analyzing a 面经 (interview experience post) from 1point3acres.com.

Post content:
<content>
{content}
</content>

Extract and classify the interview questions/topics mentioned into three categories:
1. behavioral - behavioral/situational questions (e.g., "tell me about a time...", values, culture fit)
2. coding - coding/algorithm/data structure problems (e.g., LeetCode-style, implementation)
3. system_design - system design questions (e.g., design a URL shortener, scalability discussion)

Return a JSON object with this exact structure:
{{
  "behavioral": ["question or topic 1", "question or topic 2"],
  "coding": ["problem description 1", "problem description 2"],
  "system_design": ["design question 1", "design question 2"],
  "rounds": <number of interview rounds mentioned, or null if unclear>,
  "result": "<pass|fail|waitlist|unknown>"
}}

Rules:
- Only include questions actually mentioned in the post. If a category has none, use [].
- Keep each item brief (1-2 sentences max).
- For coding problems, describe the problem type/algorithm, not just "coding question".
- Extract the interview result from context clues (pass/offer/reject/waitlist).
- Return ONLY the JSON, no explanation.
"""


async def crawl_post_content(page, url: str) -> str:
    """Fetch post content from a thread URL."""
    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(2000)

    # Extract all posts' text from the thread (first post = main content, replies = context)
    content = await page.evaluate("""() => {
        const posts = document.querySelectorAll('#postlist .t_f');
        return Array.from(posts).map(p => p.innerText.trim()).filter(t => t.length > 20).join('\\n\\n---\\n\\n');
    }""")
    return content or ""


def classify_post(client: anthropic.Anthropic, content: str) -> dict:
    """Call Claude Haiku to classify interview questions in the post."""
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": CLASSIFY_PROMPT.format(content=content[:6000])  # cap to ~6K chars
        }]
    )
    text = next((b.text for b in response.content if b.type == "text"), "")
    # Strip markdown code fences if present
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        text = text.rsplit("```", 1)[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"behavioral": [], "coding": [], "system_design": [], "rounds": None, "result": "unknown", "_parse_error": text}


def find_latest_posts_cache() -> Path | None:
    """Find the most recently modified posts list JSON in cache/."""
    files = sorted(CACHE_DIR.glob("mianjing_*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    return files[0] if files else None


def generate_report(posts_meta: list[dict], parsed_results: dict[str, dict], source_file: str) -> str:
    """Generate a markdown report aggregating all classified questions."""
    from collections import Counter

    total = len(parsed_results)
    behavioral_all: list[str] = []
    coding_all: list[str] = []
    system_design_all: list[str] = []
    results_counter: Counter = Counter()
    rounds_list: list[int] = []

    for tid, parsed in parsed_results.items():
        behavioral_all.extend(parsed.get("behavioral") or [])
        coding_all.extend(parsed.get("coding") or [])
        system_design_all.extend(parsed.get("system_design") or [])
        result = parsed.get("result", "unknown")
        results_counter[result] += 1
        rounds = parsed.get("rounds")
        if isinstance(rounds, int):
            rounds_list.append(rounds)

    # Find posts metadata for linking
    tid_to_meta = {p["tid"]: p for p in posts_meta}

    lines = [
        f"# 面经分析报告",
        f"",
        f"**数据来源**: `{source_file}`",
        f"**分析帖子数**: {total}",
        f"",
        f"## 面试结果统计",
        "",
    ]
    for result, count in sorted(results_counter.items(), key=lambda x: -x[1]):
        lines.append(f"- {result}: {count} 篇")

    if rounds_list:
        avg_rounds = sum(rounds_list) / len(rounds_list)
        lines.append(f"- 平均面试轮数: {avg_rounds:.1f} (来自 {len(rounds_list)} 篇)")

    lines += [
        "",
        f"## Behavioral 行为面试题 ({len(behavioral_all)} 条)",
        "",
    ]
    for q in behavioral_all:
        lines.append(f"- {q}")

    lines += [
        "",
        f"## Coding 编程题 ({len(coding_all)} 条)",
        "",
    ]
    for q in coding_all:
        lines.append(f"- {q}")

    lines += [
        "",
        f"## System Design 系统设计题 ({len(system_design_all)} 条)",
        "",
    ]
    for q in system_design_all:
        lines.append(f"- {q}")

    lines += [
        "",
        "## 帖子详情",
        "",
    ]
    for tid, parsed in parsed_results.items():
        meta = tid_to_meta.get(tid, {})
        title = meta.get("title", tid)
        url = meta.get("url", "")
        result = parsed.get("result", "unknown")
        rounds = parsed.get("rounds")
        rounds_str = f" | {rounds}轮" if rounds else ""
        lines.append(f"### [{title}]({url})")
        lines.append(f"*结果: {result}{rounds_str}*")
        for cat, label in [("behavioral", "Behavioral"), ("coding", "Coding"), ("system_design", "System Design")]:
            items = parsed.get(cat) or []
            if items:
                lines.append(f"**{label}**: {', '.join(items[:3])}" + (" ..." if len(items) > 3 else ""))
        lines.append("")

    return "\n".join(lines)


async def run(args: argparse.Namespace) -> None:
    # --- Step 0: find posts list ---
    posts_file = Path(args.posts) if args.posts else find_latest_posts_cache()
    if not posts_file or not posts_file.exists():
        print(f"ERROR: No posts cache found. Run crawl_mianjing.py first, or pass --posts FILE")
        sys.exit(1)

    posts: list[dict] = json.loads(posts_file.read_text(encoding="utf-8"))
    print(f"Loaded {len(posts)} posts from {posts_file}")

    if args.max_posts and args.max_posts > 0:
        posts = posts[:args.max_posts]
        print(f"Processing first {len(posts)} posts (--max-posts)")

    POSTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    PARSED_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # --- Step 1: Crawl post content ---
    posts_needing_crawl = [p for p in posts if args.force_crawl or not (POSTS_CACHE_DIR / f"{p['tid']}.json").exists()]
    print(f"Posts needing content crawl: {len(posts_needing_crawl)}")

    if posts_needing_crawl:
        res = openBrowser(args.browser_id)
        data = res.get("data") or {}
        ws = data.get("ws")
        if not ws:
            raise RuntimeError(f"openBrowser missing ws: {res}")

        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(ws)
            context = browser.contexts[0]
            page = await context.new_page()

            for i, post in enumerate(posts_needing_crawl, 1):
                tid = post["tid"]
                url = post["url"]
                cache_file = POSTS_CACHE_DIR / f"{tid}.json"
                print(f"  [{i}/{len(posts_needing_crawl)}] Crawling tid={tid}: {post['title'][:50]}")
                try:
                    content = await crawl_post_content(page, url)
                    cache_file.write_text(
                        json.dumps({"tid": tid, "url": url, "title": post["title"], "content": content},
                                   ensure_ascii=False, indent=2),
                        encoding="utf-8"
                    )
                    print(f"    → {len(content)} chars saved")
                except Exception as e:
                    print(f"    → ERROR: {e}")

            if not args.keep_open:
                await page.close()
                await browser.close()
                closeBrowser(args.browser_id)
            else:
                await browser.close()

    # --- Step 2: Classify with Claude Haiku ---
    if args.crawl_only:
        print("\n--crawl-only: skipping classification and report generation.")
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    posts_needing_parse = [
        p for p in posts
        if (POSTS_CACHE_DIR / f"{p['tid']}.json").exists()
        and (args.force_parse or not (PARSED_CACHE_DIR / f"{p['tid']}.json").exists())
    ]
    print(f"\nPosts needing classification: {len(posts_needing_parse)}")

    for i, post in enumerate(posts_needing_parse, 1):
        tid = post["tid"]
        post_data = json.loads((POSTS_CACHE_DIR / f"{tid}.json").read_text(encoding="utf-8"))
        content = post_data.get("content", "")
        if not content:
            print(f"  [{i}/{len(posts_needing_parse)}] Skip tid={tid} (empty content)")
            continue

        print(f"  [{i}/{len(posts_needing_parse)}] Classifying tid={tid}: {post['title'][:50]}")
        try:
            result = classify_post(client, content)
            parsed_file = PARSED_CACHE_DIR / f"{tid}.json"
            parsed_file.write_text(
                json.dumps({"tid": tid, **result}, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            b = len(result.get("behavioral") or [])
            c = len(result.get("coding") or [])
            s = len(result.get("system_design") or [])
            print(f"    → behavioral={b}, coding={c}, system_design={s}, result={result.get('result')}")
        except Exception as e:
            print(f"    → ERROR: {e}")

    # --- Step 3: Generate report ---
    parsed_results: dict[str, dict] = {}
    for post in posts:
        tid = post["tid"]
        parsed_file = PARSED_CACHE_DIR / f"{tid}.json"
        if parsed_file.exists():
            parsed_results[tid] = json.loads(parsed_file.read_text(encoding="utf-8"))

    if not parsed_results:
        print("\nNo parsed results available. Cannot generate report.")
        return

    print(f"\nGenerating report from {len(parsed_results)} classified posts...")
    report = generate_report(posts, parsed_results, str(posts_file))

    if args.report:
        report_path = Path(args.report)
    else:
        stem = posts_file.stem
        report_path = Path(f"report_{stem}.md")

    report_path.write_text(report, encoding="utf-8")
    print(f"Report saved to {report_path}")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Parse and classify 面经 posts using Claude Haiku.")
    p.add_argument("--posts", default="", help="Path to posts list JSON (default: auto-detect latest in cache/)")
    p.add_argument("--browser-id", default=DEFAULT_BROWSER_ID, dest="browser_id")
    p.add_argument("--max-posts", type=int, default=0, dest="max_posts",
                   help="Max posts to process (default: 0 = all)")
    p.add_argument("--force-crawl", action="store_true", dest="force_crawl",
                   help="Re-crawl post content even if cached")
    p.add_argument("--force-parse", action="store_true", dest="force_parse",
                   help="Re-classify even if cached")
    p.add_argument("--keep-open", action="store_true", dest="keep_open",
                   help="Leave Bit browser open after crawling")
    p.add_argument("--report", default="", help="Output report path (default: auto-named)")
    p.add_argument("--crawl-only", action="store_true", dest="crawl_only",
                   help="Only crawl post content, skip classification and report")
    return p.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args(sys.argv[1:])
    asyncio.run(run(args))
