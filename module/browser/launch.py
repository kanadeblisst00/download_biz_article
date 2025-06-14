import asyncio
import playwright
from loguru import logger
from fastapi import FastAPI
from playwright.async_api import async_playwright, BrowserContext, Playwright, Browser
from ..settings import CHROMIUM_EXECUTABLE_PATH


class ChromeManager:

    default_chrome_args = [
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--disable-blink-features=AutomationControlled",
        "--deny-permission-prompts",
        '--disable-notifications',
        "--disable-background-networking",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-breakpad",
        "--disable-client-side-phishing-detection",
        "--disable-component-extensions-with-background-pages",
        "--disable-default-apps",
        "--disable-extensions",
        "--disable-features=TranslateUI",
        "--disable-hang-monitor",
        "--disable-ipc-flooding-protection",
        "--disable-popup-blocking",
        "--disable-prompt-on-repost",
        "--disable-sync",
        "--force-color-profile=srgb",
        "--metrics-recording-only",
        "--no-first-run",
        "--password-store=basic",
        "--use-mock-keychain",
    ]

    def __init__(self, app: FastAPI=None, settings: dict=None):
        self.app = app
        self.headless = {"true": True, "false": False}[settings["base"].get("headless", "false")]
        self.executable_path = settings["base"].get("chrome_path") or CHROMIUM_EXECUTABLE_PATH
        self._playwright_manager:Playwright = None
        self._playwright_browser:Browser = None
        self._playwright_context:BrowserContext = None
        self._playwright_browser_lock = asyncio.Lock()
        self._playwright_screenshot_lock = asyncio.Lock()
        self._browser_event = asyncio.Event()
        self._exit = False
    
    async def _launch(self):
        if self._browser_event.is_set():
            return
        await self._cleanup()
        async with self._playwright_browser_lock:
            self._playwright_manager =  await async_playwright().start()
            self._playwright_browser = await self._playwright_manager.chromium.launch(
                headless=self.headless,
                executable_path=self.executable_path,
                channel="chromium",
                slow_mo=50,
                args=self.default_chrome_args
            ) 
            self._playwright_context = await self._playwright_browser.new_context(
                viewport={"width": 1440, "height": 980},
                ignore_https_errors=True,
                accept_downloads=False,
            )
            await self.create_tab()
        self._browser_event.set()
    
    async def launch(self):
        await self._launch()
    
    async def create_tab(self):
        page = await self._playwright_context.new_page()
        return page
    
    async def __aenter__(self):
        self._browser_event.clear()
        await self.launch()
        return {"chrome_manager":self}
    
    async def _cleanup_playwright(self, playwright_obj):
        if playwright_obj:
            try:
                await playwright_obj.close()
            except playwright._impl._errors.TargetClosedError:
                pass
            except Exception as e:
                logger.info(f"处理浏览器关闭异常: {e}")
    
    async def _cleanup(self):
        await self._cleanup_playwright(self._playwright_context)
        await self._cleanup_playwright(self._playwright_browser)
        await self._cleanup_playwright(self._playwright_manager)
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._exit = True
        await self._cleanup()
        
