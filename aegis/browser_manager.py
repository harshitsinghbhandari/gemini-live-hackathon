import asyncio
import logging
import os
from typing import Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger("aegis.browser_manager")

class BrowserManager:
    _instance: Optional['BrowserManager'] = None
    _lock = asyncio.Lock()

    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    @classmethod
    async def get_instance(cls) -> 'BrowserManager':
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    async def start(self):
        if not self.playwright:
            self.playwright = await async_playwright().start()
            headless = os.environ.get("AEGIS_BROWSER_HEADLESS", "true").lower() == "true"
            self.browser = await self.playwright.chromium.launch(headless=headless)
            self.context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            self.page = await self.context.new_page()
            logger.info("Playwright Browser started successfully.")

    async def get_page(self) -> Page:
        if not self.page:
            await self.start()
        return self.page

    async def close(self):
        async with self._lock:
            if self.browser:
                await self.browser.close()
                self.browser = None
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            self.page = None
            self.context = None
            logger.info("Playwright Browser closed.")

    async def take_screenshot(self) -> bytes:
        page = await self.get_page()
        return await page.screenshot(type='jpeg', quality=70)

# Global helper to get the manager
async def get_browser_manager() -> BrowserManager:
    return await BrowserManager.get_instance()
