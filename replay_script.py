import asyncio
import json
import os
import sys
from pathlib import Path
import urllib.parse
from patchright.async_api import async_playwright, Page, BrowserContext
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

SENSITIVE_DATA = {}


# --- Helper Functions (from playwright_script_helpers.py) ---
from patchright.async_api import Page


# --- Helper Function for Replacing Sensitive Data ---
def replace_sensitive_data(text: str, sensitive_map: dict) -> str:
	"""Replaces sensitive data placeholders in text."""
	if not isinstance(text, str):
		return text
	for placeholder, value in sensitive_map.items():
		replacement_value = str(value) if value is not None else ''
		text = text.replace(f'<secret>{placeholder}</secret>', replacement_value)
	return text


# --- Helper Function for Robust Action Execution ---
class PlaywrightActionError(Exception):
	"""Custom exception for errors during Playwright script action execution."""

	pass


async def _try_locate_and_act(page: Page, selector: str, action_type: str, text: str | None = None, step_info: str = '') -> None:
	"""
	Attempts an action (click/fill) with XPath fallback by trimming prefixes.
	Raises PlaywrightActionError if the action fails after all fallbacks.
	"""
	print(f'Attempting {action_type} ({step_info}) using selector: {repr(selector)}')
	original_selector = selector
	MAX_FALLBACKS = 50  # Increased fallbacks
	# Increased timeouts for potentially slow pages
	INITIAL_TIMEOUT = 10000  # Milliseconds for the first attempt (10 seconds)
	FALLBACK_TIMEOUT = 1000  # Shorter timeout for fallback attempts (1 second)

	try:
		locator = page.locator(selector).first
		if action_type == 'click':
			await locator.click(timeout=INITIAL_TIMEOUT)
		elif action_type == 'fill' and text is not None:
			await locator.fill(text, timeout=INITIAL_TIMEOUT)
		else:
			# This case should ideally not happen if called correctly
			raise PlaywrightActionError(f"Invalid action_type '{action_type}' or missing text for fill. ({step_info})")
		print(f"  Action '{action_type}' successful with original selector.")
		await page.wait_for_timeout(500)  # Wait after successful action
		return  # Successful exit
	except Exception as e:
		print(f"  Warning: Action '{action_type}' failed with original selector ({repr(selector)}): {e}. Starting fallback...")

		# Fallback only works for XPath selectors
		if not selector.startswith('xpath='):
			# Raise error immediately if not XPath, as fallback won't work
			raise PlaywrightActionError(
				f"Action '{action_type}' failed. Fallback not possible for non-XPath selector: {repr(selector)}. ({step_info})"
			)

		xpath_parts = selector.split('=', 1)
		if len(xpath_parts) < 2:
			raise PlaywrightActionError(
				f"Action '{action_type}' failed. Could not extract XPath string from selector: {repr(selector)}. ({step_info})"
			)
		xpath = xpath_parts[1]  # Correctly get the XPath string

		segments = [seg for seg in xpath.split('/') if seg]

		for i in range(1, min(MAX_FALLBACKS + 1, len(segments))):
			trimmed_xpath_raw = '/'.join(segments[i:])
			fallback_xpath = f'xpath=//{trimmed_xpath_raw}'

			print(f'    Fallback attempt {i}/{MAX_FALLBACKS}: Trying selector: {repr(fallback_xpath)}')
			try:
				locator = page.locator(fallback_xpath).first
				if action_type == 'click':
					await locator.click(timeout=FALLBACK_TIMEOUT)
				elif action_type == 'fill' and text is not None:
					try:
						await locator.clear(timeout=FALLBACK_TIMEOUT)
						await page.wait_for_timeout(100)
					except Exception as clear_error:
						print(f'    Warning: Failed to clear field during fallback ({step_info}): {clear_error}')
					await locator.fill(text, timeout=FALLBACK_TIMEOUT)

				print(f"    Action '{action_type}' successful with fallback selector: {repr(fallback_xpath)}")
				await page.wait_for_timeout(500)
				return  # Successful exit after fallback
			except Exception as fallback_e:
				print(f'    Fallback attempt {i} failed: {fallback_e}')
				if i == MAX_FALLBACKS:
					# Raise exception after exhausting fallbacks
					raise PlaywrightActionError(
						f"Action '{action_type}' failed after {MAX_FALLBACKS} fallback attempts. Original selector: {repr(original_selector)}. ({step_info})"
					)

	# This part should not be reachable if logic is correct, but added as safeguard
	raise PlaywrightActionError(f"Action '{action_type}' failed unexpectedly for {repr(original_selector)}. ({step_info})")

# --- End Helper Functions ---
async def run_generated_script():
    global SENSITIVE_DATA
    async with async_playwright() as p:
        browser = None
        context = None
        page = None
        exit_code = 0 # Default success exit code
        try:
            print('Launching chromium browser...')
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(no_viewport=True)
            print('Browser context created.')
            # Initial page handling
            if context.pages:
                page = context.pages[0]
                print('Using initial page provided by context.')
            else:
                page = await context.new_page()
                print('Created a new page as none existed.')

            # Wait 15 seconds for manual captcha solving
            print('⏱️  Waiting 15 seconds for manual captcha solving...')
            await asyncio.sleep(15)
            print('✅  15-second wait completed, continuing with automation')
            print('\n--- Starting Generated Script Execution ---')

            # --- Step 1 ---
            # Action 1
            search_url = f"https://www.google.com/search?q={ urllib.parse.quote_plus(replace_sensitive_data("MCPs site:medium.com", SENSITIVE_DATA)) }&udm=14"
            print(f"Searching Google for query related to: { replace_sensitive_data("MCPs site:medium.com", SENSITIVE_DATA) } (Step 1, Action 1)")
            await page.goto(search_url, timeout=5000)
            await page.wait_for_load_state('load', timeout=5000)
            await page.wait_for_timeout(1000)

            # --- Step 2 ---
            # Action 2
            await _try_locate_and_act(page, "xpath=//html/body/div[2]/div[3]/div[2]/div/label", "click", step_info="Step 2, Action 1")

            # --- Step 3 ---
            # Action 3
            await _try_locate_and_act(page, "xpath=//html/body/div/div/div[3]/div[2]/div[1]/div[1]/div[1]/button", "click", step_info="Step 3, Action 1")
            # Action 4
            await _try_locate_and_act(page, "xpath=//html/body/div/div/div[3]/div[2]/div[1]/div[1]/div[2]/button", "click", step_info="Step 3, Action 2")

            # --- Step 4 ---
            # Action 5
            await _try_locate_and_act(page, "xpath=//html/body/div/div/div[3]/div[2]/div[1]/div[1]/div[2]/button", "click", step_info="Step 4, Action 1")

            # --- Step 5 ---
            # Action 6
            await _try_locate_and_act(page, "xpath=//html/body/div/div/div[2]/div/div[2]/div[1]/div[1]/div[2]/button", "click", step_info="Step 5, Action 1")

            # --- Step 6 ---
            # Action 7
            await _try_locate_and_act(page, "xpath=//html/body/div/div/div[2]/div/div[2]/div[1]/div[1]/div[2]/button", "click", step_info="Step 6, Action 1")

            # --- Step 7 ---
            # Action 8
            await _try_locate_and_act(page, "xpath=//html/body/div[3]/div/div[12]/div/div/div[2]/div[2]/div/div/div[1]/div/div/div[1]/div/div/span/a", "click", step_info="Step 7, Action 1")

            # --- Step 8 ---
            # Action 9
            # Action: extract_content (Goal: summarize the article on MCPs) - Skipped in Playwright script (Step 8, Action 1)

            # --- Step 9 ---
            # Action 10
            await asyncio.sleep(60)  # Wait 1 minute (important) before going back
            print(f"Navigating back using browser history (Step 9, Action 1)")
            await page.go_back(timeout=5000)
            await page.wait_for_load_state('load', timeout=5000)
            await page.wait_for_timeout(1000)

            # --- Step 10 ---
            # Action 11
            search_url = f"https://www.google.com/search?q={ urllib.parse.quote_plus(replace_sensitive_data("MCPs site:medium.com", SENSITIVE_DATA)) }&udm=14"
            print(f"Searching Google for query related to: { replace_sensitive_data("MCPs site:medium.com", SENSITIVE_DATA) } (Step 10, Action 1)")
            await page.goto(search_url, timeout=5000)
            await page.wait_for_load_state('load', timeout=5000)
            await page.wait_for_timeout(1000)

            # --- Step 11 ---
            # Action 12
            await _try_locate_and_act(page, "xpath=//html/body/div[3]/div/div[12]/div/div/div[2]/div[2]/div/div/div[2]/div/div/div[1]/div/div/span/a", "click", step_info="Step 11, Action 1")

            # --- Step 12 ---
            # Action 13
            # Action: extract_content (Goal: Extract detailed information about MCPs from this Medium article.) - Skipped in Playwright script (Step 12, Action 1)

            # --- Step 13 ---
            # Action 14
            search_url = f"https://www.google.com/search?q={ urllib.parse.quote_plus(replace_sensitive_data("MCPs site:medium.com", SENSITIVE_DATA)) }&udm=14"
            print(f"Searching Google for query related to: { replace_sensitive_data("MCPs site:medium.com", SENSITIVE_DATA) } (Step 13, Action 1)")
            await page.goto(search_url, timeout=5000)
            await page.wait_for_load_state('load', timeout=5000)
            await page.wait_for_timeout(1000)

            # --- Step 14 ---
            # Action 15
            await _try_locate_and_act(page, "xpath=//html/body/div[3]/div/div[12]/div/div/div[2]/div[2]/div/div/div[4]/div/div/div[1]/div/div/span/a", "click", step_info="Step 14, Action 1")

            # --- Step 15 ---
            # Action 16
            # Action: extract_content (Goal: Extract detailed information about MCPs from this Medium article.) - Skipped in Playwright script (Step 15, Action 1)

            # --- Step 16 ---
            # Action 17
            search_url = f"https://www.google.com/search?q={ urllib.parse.quote_plus(replace_sensitive_data("MCPs site:medium.com", SENSITIVE_DATA)) }&udm=14"
            print(f"Searching Google for query related to: { replace_sensitive_data("MCPs site:medium.com", SENSITIVE_DATA) } (Step 16, Action 1)")
            await page.goto(search_url, timeout=5000)
            await page.wait_for_load_state('load', timeout=5000)
            await page.wait_for_timeout(1000)

            # --- Step 17 ---
            # Action 18
            await _try_locate_and_act(page, "xpath=//html/body/div[3]/div/div[12]/div/div/div[2]/div[2]/div/div/div[6]/div/div/div[1]/div/div/span/a", "click", step_info="Step 17, Action 1")

            # --- Step 18 ---
            # Action 19
            # Action: extract_content (Goal: Extract detailed information about MCPs from this Medium article.) - Skipped in Playwright script (Step 18, Action 1)

            # --- Step 19 ---
            # Action 20
            search_url = f"https://www.google.com/search?q={ urllib.parse.quote_plus(replace_sensitive_data("MCPs site:medium.com", SENSITIVE_DATA)) }&udm=14"
            print(f"Searching Google for query related to: { replace_sensitive_data("MCPs site:medium.com", SENSITIVE_DATA) } (Step 19, Action 1)")
            await page.goto(search_url, timeout=5000)
            await page.wait_for_load_state('load', timeout=5000)
            await page.wait_for_timeout(1000)

            # --- Step 20 ---
            # Action 21
            await _try_locate_and_act(page, "xpath=//html/body/div[3]/div/div[12]/div/div/div[2]/div[2]/div/div/div[8]/div/div/div[1]/div/div/span/a/div", "click", step_info="Step 20, Action 1")

            # --- Step 21 ---
            # Action 22
            # Action: extract_content (Goal: Extract detailed information about MCPs from the article.) - Skipped in Playwright script (Step 21, Action 1)

            # --- Step 22 ---
            # Action 23
            print("\n--- Task marked as Done by agent (Step 22, Action 1) ---")
            print(f"Agent reported success: True")
            # Final Message from agent (may contain placeholders):
            final_message = replace_sensitive_data("### Summary of MCPs from Medium Articles\n\n1. **Understanding MCPs: Transforming AI Beyond Limits**\n   - **Author**: Abu Bakar\n   - **Summary**: MCPs enhance AI capabilities by providing context awareness, tool integration, and task execution. They address limitations of LLMs like static knowledge and lack of tool access.\n\n2. **What Are MCPs and Why Should You Care?**\n   - **Author**: Nilupul Manodya\n   - **Summary**: MCPs standardize AI interactions with external systems, enabling reliable and scalable communication. They act as a middleware layer, similar to an OS kernel.\n\n3. **10 Open-Source MCPs That Make Your AI Agents Smarter**\n   - **Author**: <devtips/>\n   - **Summary**: MCPs provide structure, memory, and coordination to AI agents, transforming them into coordinated teams. The article introduces 10 open-source MCPs.\n\n4. **MCPs + LangChain + FastAPI: From Zero to Hero**\n   - **Author**: Andres Felipe Tellez Yepes\n   - **Summary**: The article provides examples of integrating MCPs with LangChain and FastAPI, showcasing client-server architectures and enhancing MCP skills.\n\n5. **MCPs, Simply Explained**\n   - **Author**: Woyera\n   - **Summary**: MCPs guide AI models in specific roles, ensuring consistency and scalability. They act as a universal plug for AI, connecting to various tools and data sources.\n\nThe articles collectively highlight MCPs as a transformative framework for AI, enhancing its ability to interact with external systems, perform tasks efficiently, and operate in various roles.", SENSITIVE_DATA)
            print(final_message)
        except PlaywrightActionError as pae:
            print(f'\n--- Playwright Action Error: {pae} ---', file=sys.stderr)
            exit_code = 1
        except Exception as e:
            print(f'\n--- An unexpected error occurred: {e} ---', file=sys.stderr)
            import traceback
            traceback.print_exc()
            exit_code = 1
        finally:
            print('\n--- Generated Script Execution Finished ---')
            print('Closing browser/context...')
            if context:
                 try: await context.close()
                 except Exception as ctx_close_err: print(f'  Warning: could not close context: {ctx_close_err}', file=sys.stderr)
            if browser:
                 try: await browser.close()
                 except Exception as browser_close_err: print(f'  Warning: could not close browser: {browser_close_err}', file=sys.stderr)
            print('Browser/context closed.')
            # Exit with the determined exit code
            if exit_code != 0:
                print(f'Script finished with errors (exit code {exit_code}).', file=sys.stderr)
                sys.exit(exit_code)

# --- Script Entry Point ---
if __name__ == '__main__':
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(run_generated_script())