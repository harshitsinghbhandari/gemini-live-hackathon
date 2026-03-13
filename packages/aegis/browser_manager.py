import asyncio
import logging
import os
from typing import Optional, List, Dict, Any
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
        self.cdp_url = os.environ.get("AEGIS_CDP_URL", "http://localhost:9222")
        self.last_som_elements: List[Dict[str, Any]] = []

    @classmethod
    async def get_instance(cls) -> 'BrowserManager':
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    async def start(self):
        if self.playwright:
            return

        self.playwright = await async_playwright().start()
        try:
            # PRIMARY: Connect via CDP to existing Chrome
            logger.info(f"Attempting CDP connection to {self.cdp_url}...")
            self.browser = await self.playwright.chromium.connect_over_cdp(self.cdp_url)
            contexts = self.browser.contexts
            if contexts:
                self.context = contexts[0]
                self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
            else:
                self.context = await self.browser.new_context()
                self.page = await self.context.new_page()
            logger.info("Possessed live Chrome instance via CDP.")
        except Exception as e:
            logger.warning(f"CDP Possession failed: {e}. Falling back to ephemeral launch.")
            headless = os.environ.get("AEGIS_BROWSER_HEADLESS", "true").lower() == "true"
            self.browser = await self.playwright.chromium.launch(headless=headless)
            self.context = await self.browser.new_context(
                viewport={'width': 1280, 'height': 800},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            self.page = await self.context.new_page()
            logger.info("Playwright Ephemeral Browser started.")

    async def get_page(self) -> Page:
        if not self.page:
            await self.start()
        return self.page

    async def health_check(self) -> bool:
        """Check if browser connection is still alive."""
        if not self.page:
            return False
        try:
            await self.page.evaluate("1")
            return True
        except Exception:
            return False

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
            logger.info("Browser session closed.")

    async def take_screenshot(self, som_overlay: bool = False) -> bytes:
        page = await self.get_page()
        
        if som_overlay:
            # LAYER A: Inject SoM Overlay
            som_script = """
            () => {
                const elements = document.querySelectorAll('a, button, input, textarea, select, [role="button"], [role="link"], [onclick], [tabindex]');
                const map = [];
                const overlay = document.createElement('div');
                overlay.id = 'aegis-som-overlay';
                overlay.style.position = 'fixed';
                overlay.style.top = '0';
                overlay.style.left = '0';
                overlay.style.width = '100%';
                overlay.style.height = '100%';
                overlay.style.pointerEvents = 'none';
                overlay.style.zIndex = '2147483647';
                document.body.appendChild(overlay);

                let idCounter = 1;
                elements.forEach(el => {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 2 && rect.height > 2) {
                        const style = window.getComputedStyle(el);
                        if (style.visibility !== 'hidden' && style.display !== 'none' && style.opacity !== '0') {
                            const box = document.createElement('div');
                            box.style.position = 'fixed';
                            box.style.left = rect.left + 'px';
                            box.style.top = rect.top + 'px';
                            box.style.width = rect.width + 'px';
                            box.style.height = rect.height + 'px';
                            box.style.border = '2px solid red';
                            box.style.boxSizing = 'border-box';
                            
                            const label = document.createElement('span');
                            label.innerText = idCounter;
                            label.style.position = 'absolute';
                            label.style.top = '-2px';
                            label.style.left = '-2px';
                            label.style.background = 'red';
                            label.style.color = 'white';
                            label.style.fontSize = '10px';
                            label.style.padding = '1px 3px';
                            label.style.fontWeight = 'bold';
                            box.appendChild(label);
                            overlay.appendChild(box);

                            map.push({
                                id: idCounter++,
                                tagName: el.tagName.toLowerCase(),
                                text: (el.innerText || el.value || el.placeholder || "").substring(0, 30),
                                box: {x: rect.left, y: rect.top, w: rect.width, h: rect.height},
                                selector: "data-aegis-id-" + (idCounter-1)
                            });
                            el.setAttribute('data-aegis-id', idCounter-1);
                        }
                    }
                });
                return map;
            }
            """
            try:
                self.last_som_elements = await page.evaluate(som_script)
                shot = await page.screenshot(type='jpeg', quality=70)
                # Cleanup
                await page.evaluate("() => document.getElementById('aegis-som-overlay')?.remove()")
                return shot
            except Exception as e:
                logger.error(f"SoM injection failed: {e}")
                return await page.screenshot(type='jpeg', quality=70)
        
        return await page.screenshot(type='jpeg', quality=70)

# Global helper to get the manager
async def get_browser_manager() -> BrowserManager:
    return await BrowserManager.get_instance()
