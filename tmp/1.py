import asyncio
from playwright.async_api import async_playwright

async def save_mhtml(url, output_file):
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path="C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(url)
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)
        # 通过CDP协议保存为MHTML
        client = await context.new_cdp_session(page)
        result = await client.send("Page.captureSnapshot", {"format": "mhtml"})
        with open(output_file, "w", encoding="utf-8", newline="") as f:
            f.write(result["data"])
        await browser.close()

if __name__ == "__main__":
    url = "https://www.baidu.com"
    output_file = "output.mhtml"
    asyncio.run(save_mhtml(url, output_file))