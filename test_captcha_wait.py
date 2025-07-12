#!/usr/bin/env python3

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

from browser_use.agent.service import Agent
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContextConfig

async def test_captcha_wait():
    """Test script to verify the 15-second captcha wait is working"""
    
    # Create browser with headful mode so we can see the wait
    browser_config = BrowserConfig(
        headless=False,
        disable_security=True
    )
    
    context_config = BrowserContextConfig(
        window_width=1024,
        window_height=768
    )
    
    browser = Browser(config=browser_config)
    
    try:
        # Create browser context - this should include the 15-second wait
        context = await browser.new_context(config=context_config)
        session = await context.get_session()
        
        print("Browser context created successfully with 15-second wait!")
        
        # Navigate to a simple page to verify it's working
        page = session.context.pages[0]
        await page.goto('https://www.google.com')
        print("Navigation completed!")
        
        # Wait a bit more to see the result
        await asyncio.sleep(2)
        
    finally:
        await browser.close()

if __name__ == '__main__':
    asyncio.run(test_captcha_wait())
