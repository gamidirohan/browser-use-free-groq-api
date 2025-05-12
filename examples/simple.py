import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio

from dotenv import load_dotenv
from langchain_deepseek import ChatDeepseek

from browser_use import Agent, BrowserConfig

load_dotenv()

# Initialize the model with DeepSeek
llm = ChatDeepseek(
    model="deepseek-chat",
    temperature=0.0,
)
task = 'Go to kayak.com and find the cheapest flight from Zurich to San Francisco on 2025-05-01'

# Configure browser to use Chromium
browser_config = BrowserConfig(
    browser_class='chromium',
    browser_binary_path='/usr/bin/chromium-browser',
    headless=False  # Set to True if you don't want to see the browser window
)

agent = Agent(task=task, llm=llm, browser_config=browser_config)


async def main():
	await agent.run()


if __name__ == '__main__':
	asyncio.run(main())
