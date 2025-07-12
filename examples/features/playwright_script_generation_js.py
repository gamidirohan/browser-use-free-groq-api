import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Ensure the project root is in the Python path if running directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from browser_use import Agent, Browser, BrowserConfig

# Load environment variables (e.g., OPENAI_API_KEY)
load_dotenv()

# Define the task for the agent
TASK_DESCRIPTION = """
1. Go to wikipedia.org
2. Search for 'Python programming'
3. Click on the first search result
4. Scroll down the page
5. Finish the task.
"""

# Define the path where the JavaScript Playwright script will be saved
SCRIPT_DIR = Path('./playwright_scripts')
SCRIPT_PATH = SCRIPT_DIR / 'wikipedia_search_script.js'

# Ensure the script directory exists
SCRIPT_DIR.mkdir(parents=True, exist_ok=True)

async def main():
	# Initialize the language model
	llm = ChatOpenAI(model='gpt-4o-mini', temperature=0.0)

	# Configure the browser
	browser_config = BrowserConfig(headless=False)
	browser = Browser(config=browser_config)

	# Configure the agent to generate JavaScript scripts
	agent = Agent(
		task=TASK_DESCRIPTION,
		llm=llm,
		browser=browser,
		save_playwright_script_path=str(SCRIPT_PATH),
		playwright_script_language='javascript',  # Generate JavaScript instead of Python
	)

	print('Running the agent to generate the JavaScript Playwright script...')
	history = None
	try:
		history = await agent.run()
		print('Agent finished running.')

		if history and history.is_successful():
			print(f'Agent completed the task successfully. Final result: {history.final_result()}')
		elif history:
			print('Agent finished, but the task might not be fully successful.')
			if history.has_errors():
				print(f'Errors encountered: {history.errors()}')
		else:
			print('Agent run did not return a history object.')

	except Exception as e:
		print(f'An error occurred during the agent run: {e}')
		# Ensure browser is closed even if agent run fails
		if browser:
			await browser.close()
		return

	# Check if JavaScript script was generated
	print(f'\nChecking if JavaScript Playwright script was generated at: {SCRIPT_PATH}')
	if SCRIPT_PATH.exists():
		print('✅ JavaScript Playwright script generated successfully!')
		print(f'Script saved to: {SCRIPT_PATH}')
		
		# Show a preview of the generated script
		print('\n--- Script Preview (first 50 lines) ---')
		with open(SCRIPT_PATH, 'r', encoding='utf-8') as f:
			lines = f.readlines()
			for i, line in enumerate(lines[:50]):
				print(f'{i+1:2d}: {line.rstrip()}')
			if len(lines) > 50:
				print(f'... and {len(lines) - 50} more lines')
		print('--- End Preview ---')
		
		print(f'\nTo run the generated JavaScript script:')
		print(f'1. Install Node.js and npm')
		print(f'2. Install Playwright: npm install playwright')
		print(f'3. Install dotenv: npm install dotenv')
		print(f'4. Run the script: node {SCRIPT_PATH}')
	else:
		print('❌ JavaScript Playwright script not found. Generation might have failed.')

	# Close the browser used by the agent
	if browser:
		await browser.close()
		print("Agent's browser closed.")

if __name__ == '__main__':
	# Ensure the script directory is clean before running (optional)
	if SCRIPT_PATH.exists():
		SCRIPT_PATH.unlink()
		print(f'Removed existing script: {SCRIPT_PATH}')

	# Run the main async function
	asyncio.run(main())
