import re
import os
import time
import base64
import asyncio
import aiofiles
import aiofiles.ospath
import playwright
from loguru import logger
from playwright.async_api import Page, BrowserContext, CDPSession
from .launch import ChromeManager


class PlaywrightHtmlManager:
    def __init__(self, chrome_manager: ChromeManager):
        self.chrome_manager = chrome_manager

    async def browser_get(self, options:dict) -> dict:
        page = await self.chrome_manager.create_tab()
        try:
            result = await self._browser_get(page, options)
        except playwright._impl._errors.TargetClosedError:
            logger.exception("浏览器状态异常，可能被关闭，正在重启浏览器!") 
            self.chrome_manager._browser_event.clear()
            await self.chrome_manager.launch()
            return await self.browser_get(options)
        # except asyncio.exceptions.CancelledError:
        #     logger.info("CancelledError, 请求被取消，正在关闭标签重新创建!")
        except:
            logger.exception("未知异常!")
        await page.close()
        return result
    
    async def _browser_get(self, page: Page, options: dict) -> dict:
        url = options["url"]
        title = options["title"]
        nickname = options.get("nickname") or "默认路径"
        pub_time = options["pub_time"]
        save_path = self.chrome_manager.app.state.save_path
        biz_path = os.path.join(save_path, nickname)
        os.makedirs(biz_path, exist_ok=True)
        filename = self._sanitize_filename(title)
        filepath = os.path.join(biz_path, filename)
        if await aiofiles.ospath.exists(f"{filepath}.pdf") and await aiofiles.ospath.exists(f"{filepath}.mhtml"):
            logger.info(f"文件已存在，跳过下载: {filepath}.pdf 和 {filepath}.mhtml")
            return 
        await self._goto(page, url)
        # 缓慢滚动页面到底部，确保图片等资源加载完成
        await page.evaluate("""
            async () => {
                const delay = ms => new Promise(res => setTimeout(res, ms));
                let totalHeight = 0;
                let distance = 300;
                while (totalHeight < document.body.scrollHeight) {
                    window.scrollBy(0, distance);
                    await delay(200);
                    totalHeight += distance;
                }
                window.scrollTo(0, document.body.scrollHeight);
                await delay(1000);
            }
        """)
        await asyncio.sleep(3)  
        download_type = self.chrome_manager.app.state.settings["base"].get("download_type") or "pdf,mhtml,html"
        download_type = download_type.lower().split(",")
        if "pdf" in download_type:
            await self._browser_save_pdf(page, filepath, pub_time)
        if "mhtml" in download_type:
            await self._browser_save_mhtml(page, filepath, pub_time)
        if "html" in download_type:
            await self._browser_get_html(page, filepath, pub_time)

    async def set_file_times(self, path, pub_time):
        if not await aiofiles.ospath.exists(path):
            return
        pub_timestamp = int(time.mktime(time.strptime(pub_time, "%Y-%m-%d %H:%M:%S")))
        try:
            os.utime(path, (pub_timestamp, pub_timestamp))
        except Exception as e:
            logger.warning(f"设置文件时间失败: {path}, 错误: {e}")

    def format_html(self, content: str) -> str:
        if not content:
            return ""
        content = content.replace('window.location.protocol', 'https:')
        content = content.replace('location.protocol', 'https://')
        content = content.replace('-webkit-user-select:none', '-webkit-user-select:text')
        content = content.replace('-webkit-user-select: none', '-webkit-user-select:text')
        content = content.replace('-moz-user-select:none', '-moz-user-select:text')
        content = content.replace('-ms-user-select:none', '-ms-user-select:text')
        content = content.replace('user-select:none', 'user-select:text')
        content = re.sub(r'src="//(.*?)"', r'src="https://\1"', content)
        content = re.sub(r'url\(//(.*?)\)', r'url\(https://\1\)', content)
        content = re.sub(r'href="//(.*?)"', r'href="https://\1"', content)
        return content.strip()
    
    async def _browser_get_html(self, page: Page, filepath, pub_time) -> str:
        try:
            content = await page.content()
        except playwright._impl._errors.Error as e:
            logger.info(f"_browser_get_html Error: {e}")
            return
        if not content:
            logger.info("没有获取到 HTML 内容，可能是页面加载失败或不支持 HTML 格式")
            return
        file_path = f"{filepath}.html"
        logger.info(f"保存 HTML 文件到: {file_path}")
        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(self.format_html(content))
        await self.set_file_times(file_path, pub_time)

    async def _browser_save_pdf(self, page: Page, filepath, pub_time) -> str:
        context: BrowserContext = self.chrome_manager._playwright_context
        client = None
        logger.info("_browser_get_pdf start")
        try:
            client: CDPSession = await context.new_cdp_session(page)
            result = await client.send("Page.printToPDF", {
                "landscape": True,
                "printBackground": True,
                "preferCSSPageSize": True
            })
        except playwright._impl._errors.Error as e:
            logger.info(f"_browser_get_pdf Error: {e}")
        else:
            pdf_content = result.get("data")
            if not pdf_content:
                logger.info("没有获取到 PDF 内容，可能是页面加载失败或不支持 PDF 格式")
                return
            pdf_content = base64.b64decode(pdf_content)
            file_path = f"{filepath}.pdf"
            logger.info(f"保存 PDF 文件到: {file_path}")
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(pdf_content)
            await self.set_file_times(file_path, pub_time)
        finally:
            if client:
                await client.detach()

    async def _browser_save_mhtml(self, page: Page, filepath, pub_time) -> str:
        context: BrowserContext = self.chrome_manager._playwright_context
        client = None
        logger.info("_browser_get_mhtml start")
        try:
            client: CDPSession = await context.new_cdp_session(page)
            result = await client.send("Page.captureSnapshot", {"format": "mhtml"})
        except playwright._impl._errors.Error as e:
            logger.info(f"_browser_get_mhtml Error: {e}")
        else:
            mhtml_content = result.get("data")
            if not mhtml_content:
                logger.info("没有获取到 mhtml 内容，可能是页面加载失败或不支持 mhtml 格式")
                return
            file_path = f"{filepath}.mhtml"
            logger.info(f"保存 mhtml 文件到: {file_path}")
            async with aiofiles.open(file_path, "w", newline="") as f:
                await f.write(mhtml_content)
            await self.set_file_times(file_path, pub_time)
        finally:
            if client:
                await client.detach()
    
    def _sanitize_filename(self, filename: str) -> str:
        # 移除或替换 Windows 文件名非法字符以及换行符、制表符等不可见字符
        filename = re.sub(r'[\r\n\t]', '', filename)
        filename = re.sub(r'[\\/:*?"<>|]', '_', filename)
        # 限制文件名长度，避免过长导致的问题
        if len(filename) > 50:
            filename = filename[:50]
        return filename.strip()

    async def _stop_page_loading(self, page: Page):
        context: BrowserContext = self.chrome_manager._playwright_context
        client = None
        logger.info("_stop_page_loading start")
        try:
            client: CDPSession = await context.new_cdp_session(page)
            result = await client.send("Page.stopLoading")
            # result = await page.evaluate('() => window.stop()')
        except playwright._impl._errors.Error as e:
            logger.info(f"_stop_page_loading Error: {e}")
        else:
            logger.info(f"_stop_page_loading result: {result}")
        finally:
            if client:
                await client.detach()

    async def _goto(self, page: Page, url, retry=0) -> dict:
        try:
            await page.goto(url, wait_until="networkidle", timeout=15000)
        except playwright._impl._errors.TimeoutError:
            logger.info(f"({url})请求超时, 尝试停止页面加载")
            try:
                await asyncio.wait_for(self._stop_page_loading(page), timeout=2)
            except asyncio.exceptions.TimeoutError:
                pass
            return {"ok": True}
        except playwright._impl._errors.Error:
            logger.exception(f"({url})请求异常")




































