import asyncio
import base64
import logging
import json
from typing import Any, Dict, Optional, List
from markdownify import markdownify as md

from .base import BaseTool, registry
from ..browser_manager import get_browser_manager
from .. import ws_server
from .. import config

logger = logging.getLogger("aegis.tools.browser")

class BrowserBaseTool(BaseTool):
    """Base class for browser tools to share common logic."""
    async def get_page(self):
        manager = await get_browser_manager()
        return await manager.get_page()

    def broadcast_action(self, action_name: str, args: Dict[str, Any], result: Dict[str, Any]):
        ws_server.broadcast("action", data={
            "tool": action_name,
            "toolkit": "browser",
            "arguments": args,
            "success": result.get("success", False),
            "output": str(result.get("output", ""))[:1000]
        })

class BrowserNavigateTool(BrowserBaseTool):
    @property
    def name(self) -> str:
        return "browser_navigate"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Navigate the browser to a specific URL. Use this for web-based tasks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to navigate to"}
                },
                "required": ["url"]
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        url = args.get("url")
        if not url:
            return {"success": False, "error": "Missing URL"}

        try:
            page = await self.get_page()
            await page.goto(url, wait_until="load")
            await page.wait_for_load_state("networkidle", timeout=5000)
            result = {"success": True, "output": f"Navigated to {url}"}
            self.broadcast_action(self.name, args, result)
            return result
        except Exception as e:
            logger.error(f"Error in {self.name}: {e}")
            return {"success": False, "error": str(e)}

class BrowserReadTool(BrowserBaseTool):
    @property
    def name(self) -> str:
        return "browser_read"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Read interactive elements on the current page. Returns a list of elements with their text, role, and a CSS selector to use with click/type tools.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            page = await self.get_page()
            # Use a robust script to extract interactive elements and generate selectors
            robust_script = """
            () => {
                const results = [];
                const candidates = document.querySelectorAll('a, button, input, textarea, select, [role="button"], [role="link"], [onclick]');

                function generateSelector(el) {
                    if (el.id) return `#${CSS.escape(el.id)}`;
                    if (el.name) return `${el.tagName.toLowerCase()}[name="${CSS.escape(el.name)}"]`;

                    let selector = el.tagName.toLowerCase();
                    if (el.classList.length > 0) {
                        selector += "." + Array.from(el.classList).map(c => CSS.escape(c)).join(".");
                    }
                    return selector;
                }

                for (const el of candidates) {
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {
                        const style = window.getComputedStyle(el);
                        if (style.visibility !== 'hidden' && style.display !== 'none') {
                            results.push({
                                tagName: el.tagName.toLowerCase(),
                                text: (el.innerText || el.value || el.placeholder || el.getAttribute('aria-label') || "").trim().substring(0, 100),
                                selector: generateSelector(el)
                            });
                        }
                    }
                    if (results.length >= 50) break;
                }
                return results;
            }
            """
            elements = await page.evaluate(robust_script)
            output = "Visible interactive elements:\n"
            for el in elements:
                output += f"- [{el['tagName']}] '{el['text']}' (selector: {el['selector']})\n"

            result = {"success": True, "output": output, "elements": elements}
            self.broadcast_action(self.name, args, {"success": True, "output": f"Found {len(elements)} elements"})
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

class BrowserClickTool(BrowserBaseTool):
    @property
    def name(self) -> str:
        return "browser_click"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Click an element in the browser using a CSS selector found via browser_read or browser_extract.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector to click"},
                    "wait_after": {"type": "boolean", "description": "Whether to wait for page navigation/load after clicking"}
                },
                "required": ["selector"]
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        selector = args.get("selector")
        wait_after = args.get("wait_after", True)
        try:
            page = await self.get_page()
            locator = page.locator(selector).first
            await locator.click(timeout=5000)
            if wait_after:
                await page.wait_for_load_state("load", timeout=10000)
                await page.wait_for_load_state("networkidle", timeout=5000)
            result = {"success": True, "output": f"Clicked {selector}"}
            self.broadcast_action(self.name, args, result)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

class BrowserTypeTool(BrowserBaseTool):
    @property
    def name(self) -> str:
        return "browser_type"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Type text into a browser input field identified by a CSS selector.",
            "parameters": {
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector for the input"},
                    "text": {"type": "string", "description": "Text to type"},
                    "press_enter": {"type": "boolean", "description": "Whether to press Enter after typing"}
                },
                "required": ["selector", "text"]
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        selector = args.get("selector")
        text = args.get("text")
        press_enter = args.get("press_enter", False)
        try:
            page = await self.get_page()
            await page.fill(selector, text, timeout=5000)
            if press_enter:
                await page.keyboard.press("Enter")
                await page.wait_for_load_state("load", timeout=10000)
                await page.wait_for_load_state("networkidle", timeout=5000)
            result = {"success": True, "output": f"Typed text into {selector}"}
            self.broadcast_action(self.name, args, result)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

class BrowserExtractTool(BrowserBaseTool):
    @property
    def name(self) -> str:
        return "browser_extract"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Extract the visible text content of the current page as Markdown. Use this to read articles, documentation, or search results.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            page = await self.get_page()
            content = await page.content()
            markdown = md(content, strip=['script', 'style'])
            result = {"success": True, "output": markdown}
            self.broadcast_action(self.name, args, {"success": True, "output": "Extracted page content"})
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

class BrowserScrollTool(BrowserBaseTool):
    @property
    def name(self) -> str:
        return "browser_scroll"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Scroll the browser page.",
            "parameters": {
                "type": "object",
                "properties": {
                    "direction": {"type": "string", "enum": ["up", "down"], "description": "Direction to scroll"},
                    "amount": {"type": "integer", "description": "Optional pixels to scroll (defaults to viewport height)"}
                },
                "required": ["direction"]
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        direction = args.get("direction")
        amount = args.get("amount")
        try:
            page = await self.get_page()
            if not amount:
                viewport = page.viewport_size
                amount = viewport['height'] if viewport else 600

            scroll_y = amount if direction == "down" else -amount
            await page.mouse.wheel(0, scroll_y)
            result = {"success": True, "output": f"Scrolled {direction}"}
            self.broadcast_action(self.name, args, result)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

class BrowserScreenshotTool(BrowserBaseTool):
    @property
    def name(self) -> str:
        return "browser_screenshot"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Capture a screenshot of the current browser viewport. Useful for visual verification of web tasks.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            manager = await get_browser_manager()
            shot_bytes = await manager.take_screenshot()
            b64_shot = base64.b64encode(shot_bytes).decode('utf-8')
            result = {
                "success": True,
                "output": "Screenshot captured",
                "base64": b64_shot,
                "mime_type": "image/jpeg"
            }
            self.broadcast_action(self.name, args, {"success": True, "output": "Screenshot captured"})
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

class BrowserWaitTool(BrowserBaseTool):
    @property
    def name(self) -> str:
        return "browser_wait"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Wait for the page to settle or for a specific element to appear.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timeout_ms": {"type": "integer", "description": "Milliseconds to wait (default 2000)"},
                    "selector": {"type": "string", "description": "Optional CSS selector to wait for"}
                }
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        timeout = args.get("timeout_ms", 2000)
        selector = args.get("selector")
        try:
            page = await self.get_page()
            if selector:
                await page.wait_for_selector(selector, timeout=timeout)
            else:
                await asyncio.sleep(timeout / 1000.0)
            result = {"success": True, "output": "Wait completed"}
            self.broadcast_action(self.name, args, result)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

class BrowserBackTool(BrowserBaseTool):
    @property
    def name(self) -> str:
        return "browser_back"

    @property
    def declaration(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": "Navigate back in browser history.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            page = await self.get_page()
            await page.go_back(wait_until="load")
            await page.wait_for_load_state("networkidle", timeout=5000)
            result = {"success": True, "output": "Navigated back"}
            self.broadcast_action(self.name, args, result)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

# Register all tools
registry.register(BrowserNavigateTool())
registry.register(BrowserReadTool())
registry.register(BrowserClickTool())
registry.register(BrowserTypeTool())
registry.register(BrowserExtractTool())
registry.register(BrowserScrollTool())
registry.register(BrowserScreenshotTool())
registry.register(BrowserWaitTool())
registry.register(BrowserBackTool())
