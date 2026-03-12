from playwright.sync_api import sync_playwright
import os

def launch_aegis_browser():
    with sync_playwright() as p:
        # Create a dedicated folder for Aegis's brain to live in
        user_data_dir = os.path.expanduser("~/Library/Application Support/AegisAgentProfile")
        
        # Launch persistent context
        # 'channel="chrome"' uses your actual Google Chrome install
        context = p.chromium.launch_persistent_context(
            user_data_dir,
            channel="chrome", 
            headless=False, 
            args=[
                "--remote-debugging-port=9222",
                # "--no-first-run",
                "--no-default-browser-check"
            ]
        )
        
        page = context.pages[0]
        page.goto("https://google.com")
        print("Aegis Domain Expanded. Browser is live.")
        input("Press Enter to close the domain...")

launch_aegis_browser()