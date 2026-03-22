from bit_api import *
import time
import asyncio
from playwright.async_api import async_playwright, Playwright



async def run(playwright: Playwright):

  # /browser/open 返回 data.ws（CDP WebSocket）；Playwright 用 connect_over_cdp(ws) 连接
  browser_id = "a290134f89cd4d40b7521657919f8366" # 窗口ID从窗口配置界面中复制，或者api创建后返回
  res = openBrowser(browser_id)
  ws = res['data']['ws']
  print("ws address ==>>> ", ws)

  chromium = playwright.chromium
  browser = await chromium.connect_over_cdp(ws)
  default_context = browser.contexts[0]

  print('new page and goto baidu')

  page = await default_context.new_page()
  await page.goto('https://creator.xiaohongshu.com/new/home')

  time.sleep(2)

  print('clsoe page and browser')
  await page.close()

  time.sleep(2)
  closeBrowser(browser_id)

async def main():
    async with async_playwright() as playwright:
      await run(playwright)

asyncio.run(main())