import json
import logging
from pathlib import Path
from typing import Any

from browser_use.browser.browser import BrowserConfig
from browser_use.browser.context import BrowserContextConfig

logger = logging.getLogger(__name__)


class PlaywrightScriptGeneratorJS:
	"""Generates a JavaScript Playwright script from AgentHistoryList."""

	def __init__(
		self,
		history_list: list[dict[str, Any]],
		sensitive_data_keys: list[str] | None = None,
		browser_config: BrowserConfig | None = None,
		context_config: BrowserContextConfig | None = None,
	):
		"""
		Initializes the JavaScript script generator.

		Args:
		    history_list: A list of dictionaries, where each dictionary represents an AgentHistory item.
		                 Expected to be raw dictionaries from `AgentHistoryList.model_dump()`.
		    sensitive_data_keys: A list of keys used as placeholders for sensitive data.
		    browser_config: Configuration from the original Browser instance.
		    context_config: Configuration from the original BrowserContext instance.
		"""
		self.history = history_list
		self.sensitive_data_keys = sensitive_data_keys or []
		self.browser_config = browser_config
		self.context_config = context_config
		self._page_counter = 0  # Track pages for tab management

		# Dictionary mapping action types to handler methods
		self._action_handlers = {
			'go_to_url': self._map_go_to_url,
			'wait': self._map_wait,
			'input_text': self._map_input_text,
			'click_element': self._map_click_element,
			'click_element_by_index': self._map_click_element,  # Map legacy action
			'scroll_down': self._map_scroll_down,
			'scroll_up': self._map_scroll_up,
			'send_keys': self._map_send_keys,
			'go_back': self._map_go_back,
			'open_tab': self._map_open_tab,
			'close_tab': self._map_close_tab,
			'switch_tab': self._map_switch_tab,
			'search_google': self._map_search_google,
			'drag_drop': self._map_drag_drop,
			'extract_content': self._map_extract_content,
			'click_download_button': self._map_click_download_button,
			'done': self._map_done,
		}

	def _generate_browser_launch_args(self) -> str:
		"""Generates the arguments object for browser launch based on BrowserConfig."""
		if not self.browser_config:
			# Default launch if no config provided
			return '{ headless: false }'

		args_dict = {
			'headless': self.browser_config.headless,
		}
		if self.browser_config.proxy:
			proxy_config = self.browser_config.proxy.model_dump()
			args_dict['proxy'] = proxy_config

		# Filter out None values
		args_dict = {k: v for k, v in args_dict.items() if v is not None}

		# Format as JavaScript object
		args_str = self._format_js_object(args_dict)
		return args_str

	def _generate_context_options(self) -> str:
		"""Generates the options object for context creation based on BrowserContextConfig."""
		if not self.context_config:
			return '{}'  # Default context

		options_dict = {}

		# Map relevant BrowserContextConfig fields to Playwright context options
		if self.context_config.user_agent:
			options_dict['userAgent'] = self.context_config.user_agent
		if self.context_config.locale:
			options_dict['locale'] = self.context_config.locale
		if self.context_config.permissions:
			options_dict['permissions'] = self.context_config.permissions
		if self.context_config.geolocation:
			options_dict['geolocation'] = self.context_config.geolocation
		if self.context_config.timezone_id:
			options_dict['timezoneId'] = self.context_config.timezone_id
		if self.context_config.http_credentials:
			options_dict['httpCredentials'] = self.context_config.http_credentials
		if self.context_config.is_mobile is not None:
			options_dict['isMobile'] = self.context_config.is_mobile
		if self.context_config.has_touch is not None:
			options_dict['hasTouch'] = self.context_config.has_touch
		if self.context_config.save_recording_path:
			options_dict['recordVideo'] = {'dir': self.context_config.save_recording_path}
		if self.context_config.save_har_path:
			options_dict['recordHar'] = {'path': self.context_config.save_har_path}

		# Handle viewport/window size
		if self.context_config.no_viewport:
			options_dict['viewport'] = None
		elif hasattr(self.context_config, 'window_width') and hasattr(self.context_config, 'window_height'):
			options_dict['viewport'] = {
				'width': self.context_config.window_width,
				'height': self.context_config.window_height,
			}

		# Filter out None values
		options_dict = {k: v for k, v in options_dict.items() if v is not None}

		# Format as JavaScript object
		options_str = self._format_js_object(options_dict)
		return options_str

	def _format_js_object(self, obj: dict) -> str:
		"""Formats a Python dictionary as a JavaScript object string."""
		def format_value(value):
			if isinstance(value, bool):
				return 'true' if value else 'false'
			elif isinstance(value, str):
				return json.dumps(value)
			elif isinstance(value, (int, float)):
				return str(value)
			elif isinstance(value, dict):
				inner_items = ', '.join(f'{k}: {format_value(v)}' for k, v in value.items())
				return f'{{ {inner_items} }}'
			elif isinstance(value, list):
				inner_items = ', '.join(format_value(v) for v in value)
				return f'[{inner_items}]'
			elif value is None:
				return 'null'
			else:
				return json.dumps(value)
		if not obj:
			return '{}'
		
		items = ', '.join(f'{key}: {format_value(value)}' for key, value in obj.items())
		return f'{{ {items} }}'
	def _get_imports_and_setup(self) -> list[str]:
		"""Generates necessary imports and setup for JavaScript."""
		return [
			"const { chromium, firefox, webkit } = require('playwright');",
			"const fs = require('fs');",
			"const path = require('path');",
			"require('dotenv').config({ override: true });",
			"",
			"// Load sensitive data from environment variables",
			"const SENSITIVE_DATA = " + self._get_sensitive_data_definitions() + ";",
			"",
		]

	def _get_sensitive_data_definitions(self) -> str:
		"""Generates the SENSITIVE_DATA object definition for JavaScript."""
		if not self.sensitive_data_keys:
			return '{}'

		items = []
		for key in self.sensitive_data_keys:
			env_var_name = key.upper()
			default_value_placeholder = f'YOUR_{env_var_name}'
			items.append(f'  "{key}": process.env.{env_var_name} || {json.dumps(default_value_placeholder)}')
		
		return '{\n' + ',\n'.join(items) + '\n}'

	def _get_helper_functions(self) -> list[str]:
		"""Generates helper functions for JavaScript."""
		return [
			"// Helper function for replacing sensitive data",
			"function replaceSensitiveData(text, sensitiveMap) {",
			"  if (typeof text !== 'string') return text;",
			"  for (const [placeholder, value] of Object.entries(sensitiveMap)) {",
			"    const searchPattern = `<secret>${placeholder}</secret>`;",
			"    const replacementValue = value || '';",
			"    text = text.replace(new RegExp(searchPattern, 'g'), replacementValue);",
			"  }",
			"  return text;",
			"}",
			"",
			"// Custom error class",
			"class PlaywrightActionError extends Error {",
			"  constructor(message) {",
			"    super(message);",
			"    this.name = 'PlaywrightActionError';",
			"  }",
			"}",
			"",
			"// Helper function for robust action execution",
			"async function tryLocateAndAct(page, selector, actionType, text = null, stepInfo = '') {",
			"  console.log(`Attempting ${actionType} (${stepInfo}) using selector: ${JSON.stringify(selector)}`);",
			"  const originalSelector = selector;",
			"  const MAX_FALLBACKS = 50;",
			"  const INITIAL_TIMEOUT = 10000; // 10 seconds",
			"  const FALLBACK_TIMEOUT = 1000; // 1 second",
			"",
			"  try {",
			"    const locator = page.locator(selector).first();",
			"    if (actionType === 'click') {",
			"      await locator.click({ timeout: INITIAL_TIMEOUT });",
			"    } else if (actionType === 'fill' && text !== null) {",
			"      await locator.fill(text, { timeout: INITIAL_TIMEOUT });",
			"    } else {",
			"      throw new PlaywrightActionError(`Invalid actionType '${actionType}' or missing text for fill. (${stepInfo})`);",
			"    }",
			"    console.log(`  Action '${actionType}' successful with original selector.`);",
			"    await page.waitForTimeout(500);",
			"    return;",
			"  } catch (e) {",
			"    console.log(`  Warning: Action '${actionType}' failed with original selector (${JSON.stringify(selector)}): ${e}. Starting fallback...`);",
			"",
			"    if (!selector.startsWith('xpath=')) {",
			"      throw new PlaywrightActionError(`Action '${actionType}' failed. Fallback not possible for non-XPath selector: ${JSON.stringify(selector)}. (${stepInfo})`);",
			"    }",
			"",
			"    const xpathParts = selector.split('=');",
			"    if (xpathParts.length < 2) {",
			"      throw new PlaywrightActionError(`Action '${actionType}' failed. Could not extract XPath string from selector: ${JSON.stringify(selector)}. (${stepInfo})`);",
			"    }",
			"    const xpath = xpathParts[1];",
			"    const segments = xpath.split('/').filter(seg => seg);",
			"",
			"    for (let i = 1; i <= Math.min(MAX_FALLBACKS, segments.length - 1); i++) {",
			"      const trimmedXpathRaw = segments.slice(i).join('/');",
			"      const fallbackXpath = `xpath=//${trimmedXpathRaw}`;",
			"",
			"      console.log(`    Fallback attempt ${i}/${MAX_FALLBACKS}: Trying selector: ${JSON.stringify(fallbackXpath)}`);",
			"      try {",
			"        const locator = page.locator(fallbackXpath).first();",
			"        if (actionType === 'click') {",
			"          await locator.click({ timeout: FALLBACK_TIMEOUT });",
			"        } else if (actionType === 'fill' && text !== null) {",
			"          try {",
			"            await locator.clear({ timeout: FALLBACK_TIMEOUT });",
			"            await page.waitForTimeout(100);",
			"          } catch (clearError) {",
			"            console.log(`    Warning: Failed to clear field during fallback (${stepInfo}): ${clearError}`);",
			"          }",
			"          await locator.fill(text, { timeout: FALLBACK_TIMEOUT });",
			"        }",
			"",
			"        console.log(`    Action '${actionType}' successful with fallback selector: ${JSON.stringify(fallbackXpath)}`);",
			"        await page.waitForTimeout(500);",
			"        return;",
			"      } catch (fallbackError) {",
			"        console.log(`    Fallback attempt ${i} failed: ${fallbackError}`);",
			"        if (i === MAX_FALLBACKS) {",
			"          throw new PlaywrightActionError(`Action '${actionType}' failed after ${MAX_FALLBACKS} fallback attempts. Original selector: ${JSON.stringify(originalSelector)}. (${stepInfo})`);",
			"        }",
			"      }",
			"    }",
			"  }",
			"",
			"  throw new PlaywrightActionError(`Action '${actionType}' failed unexpectedly for ${JSON.stringify(originalSelector)}. (${stepInfo})`);",
			"}",
			"",
		]

	def _get_goto_timeout(self) -> int:
		"""Gets the page navigation timeout in milliseconds."""
		default_timeout = 90000  # Default 90 seconds
		if self.context_config and self.context_config.maximum_wait_page_load_time:
			# Convert seconds to milliseconds
			return int(self.context_config.maximum_wait_page_load_time * 1000)
		return default_timeout

	def _get_selector_for_action(self, history_item: dict, action_index_in_step: int) -> str | None:
		"""
		Gets the selector (preferring XPath) for a given action index within a history step.
		Formats the XPath correctly for Playwright.
		"""
		state = history_item.get('state')
		if not isinstance(state, dict):
			return None
		interacted_elements = state.get('interacted_element')
		if not isinstance(interacted_elements, list):
			return None
		if action_index_in_step >= len(interacted_elements):
			return None
		element_data = interacted_elements[action_index_in_step]
		if not isinstance(element_data, dict):
			return None

		# Prioritize XPath
		xpath = element_data.get('xpath')
		if isinstance(xpath, str) and xpath.strip():
			if not xpath.startswith('xpath=') and not xpath.startswith('/') and not xpath.startswith('//'):
				xpath_selector = f'xpath={xpath}'
			elif xpath.startswith('/') and not xpath.startswith('//'):
				xpath_selector = f'xpath=//{xpath}'  # Make relative if not already
			elif not xpath.startswith('xpath='):
				xpath_selector = f'xpath={xpath}'  # Add prefix if missing
			else:
				xpath_selector = xpath
			return xpath_selector

		# Fallback to CSS selector if XPath is missing
		css_selector = element_data.get('css_selector')
		if isinstance(css_selector, str) and css_selector.strip():
			return css_selector  # Use CSS selector as is

		logger.warning(
			f'Could not find a usable XPath or CSS selector for action index {action_index_in_step} (element index {element_data.get("highlight_index", "N/A")}).'
		)
		return None

	# --- Action Mapping Methods ---
	def _map_go_to_url(self, params: dict, step_info_str: str, **kwargs) -> list[str]:
		url = params.get('url')
		goto_timeout = self._get_goto_timeout()
		script_lines = []
		if url and isinstance(url, str):
			escaped_url = json.dumps(url)
			script_lines.append(f"    console.log(`Navigating to: {url} ({step_info_str})`);")
			script_lines.append(f"    await page.goto({escaped_url}, {{ timeout: {goto_timeout} }});")
			script_lines.append(f"    await page.waitForLoadState('load', {{ timeout: {goto_timeout} }});")
			script_lines.append("    await page.waitForTimeout(1000);")
		else:
			script_lines.append(f"    // Skipping go_to_url ({step_info_str}): missing or invalid url")
		return script_lines

	def _map_wait(self, params: dict, step_info_str: str, **kwargs) -> list[str]:
		seconds = params.get('seconds', 3)
		try:
			wait_seconds = int(seconds)
		except (ValueError, TypeError):
			wait_seconds = 3
		return [
			f"    console.log(`Waiting for {wait_seconds} seconds... ({step_info_str})`);",
			f"    await page.waitForTimeout({wait_seconds * 1000});",
		]

	def _map_input_text(
		self, params: dict, history_item: dict, action_index_in_step: int, step_info_str: str, **kwargs
	) -> list[str]:
		index = params.get('index')
		text = params.get('text', '')
		selector = self._get_selector_for_action(history_item, action_index_in_step)
		script_lines = []
		if selector and index is not None:
			clean_text_expression = f'replaceSensitiveData({json.dumps(str(text))}, SENSITIVE_DATA)'
			escaped_selector = json.dumps(selector)
			escaped_step_info = json.dumps(step_info_str)
			script_lines.append(
				f"    await tryLocateAndAct(page, {escaped_selector}, 'fill', {clean_text_expression}, {escaped_step_info});"
			)
		else:
			script_lines.append(
				f"    // Skipping input_text ({step_info_str}): missing index ({index}) or selector ({selector})"
			)
		return script_lines

	def _map_click_element(
		self, params: dict, history_item: dict, action_index_in_step: int, step_info_str: str, action_type: str, **kwargs
	) -> list[str]:
		if action_type == 'click_element_by_index':
			logger.warning(f"Mapping legacy 'click_element_by_index' to 'click_element' ({step_info_str})")
		index = params.get('index')
		selector = self._get_selector_for_action(history_item, action_index_in_step)
		script_lines = []
		if selector and index is not None:
			escaped_selector = json.dumps(selector)
			escaped_step_info = json.dumps(step_info_str)
			script_lines.append(
				f"    await tryLocateAndAct(page, {escaped_selector}, 'click', null, {escaped_step_info});"
			)
		else:
			script_lines.append(
				f"    // Skipping {action_type} ({step_info_str}): missing index ({index}) or selector ({selector})"
			)
		return script_lines

	def _map_scroll_down(self, params: dict, step_info_str: str, **kwargs) -> list[str]:
		amount = params.get('amount')
		script_lines = []
		if amount and isinstance(amount, int):
			script_lines.append(f"    console.log(`Scrolling down by {amount} pixels ({step_info_str})`);")
			script_lines.append(f"    await page.evaluate(() => window.scrollBy(0, {amount}));")
		else:
			script_lines.append(f"    console.log(`Scrolling down by one page height ({step_info_str})`);")
			script_lines.append("    await page.evaluate(() => window.scrollBy(0, window.innerHeight));")
		script_lines.append("    await page.waitForTimeout(500);")
		return script_lines

	def _map_scroll_up(self, params: dict, step_info_str: str, **kwargs) -> list[str]:
		amount = params.get('amount')
		script_lines = []
		if amount and isinstance(amount, int):
			script_lines.append(f"    console.log(`Scrolling up by {amount} pixels ({step_info_str})`);")
			script_lines.append(f"    await page.evaluate(() => window.scrollBy(0, -{amount}));")
		else:
			script_lines.append(f"    console.log(`Scrolling up by one page height ({step_info_str})`);")
			script_lines.append("    await page.evaluate(() => window.scrollBy(0, -window.innerHeight));")
		script_lines.append("    await page.waitForTimeout(500);")
		return script_lines

	def _map_send_keys(self, params: dict, step_info_str: str, **kwargs) -> list[str]:
		keys = params.get('keys')
		script_lines = []
		if keys and isinstance(keys, str):
			escaped_keys = json.dumps(keys)
			script_lines.append(f"    console.log(`Sending keys: {keys} ({step_info_str})`);")
			script_lines.append(f"    await page.keyboard.press({escaped_keys});")
			script_lines.append("    await page.waitForTimeout(500);")
		else:
			script_lines.append(f"    // Skipping send_keys ({step_info_str}): missing or invalid keys")
		return script_lines

	def _map_go_back(self, params: dict, step_info_str: str, **kwargs) -> list[str]:
		goto_timeout = self._get_goto_timeout()
		return [
			"    await page.waitForTimeout(60000); // Wait 1 minute (important) before going back",
			f"    console.log(`Navigating back using browser history ({step_info_str})`);",
			f"    await page.goBack({{ timeout: {goto_timeout} }});",
			f"    await page.waitForLoadState('load', {{ timeout: {goto_timeout} }});",
			"    await page.waitForTimeout(1000);",
		]

	def _map_open_tab(self, params: dict, step_info_str: str, **kwargs) -> list[str]:
		url = params.get('url')
		goto_timeout = self._get_goto_timeout()
		script_lines = []
		if url and isinstance(url, str):
			escaped_url = json.dumps(url)
			script_lines.append(f"    console.log(`Opening new tab and navigating to: {url} ({step_info_str})`);")
			script_lines.append("    page = await context.newPage();")
			script_lines.append(f"    await page.goto({escaped_url}, {{ timeout: {goto_timeout} }});")
			script_lines.append(f"    await page.waitForLoadState('load', {{ timeout: {goto_timeout} }});")
			script_lines.append("    await page.waitForTimeout(1000);")
			self._page_counter += 1  # Increment page counter
		else:
			script_lines.append(f"    // Skipping open_tab ({step_info_str}): missing or invalid url")
		return script_lines

	def _map_close_tab(self, params: dict, step_info_str: str, **kwargs) -> list[str]:
		page_id = params.get('page_id')
		script_lines = []
		if page_id is not None:
			script_lines.extend(
				[
					f"    console.log(`Attempting to close tab with page_id {page_id} ({step_info_str})`);",
					f"    if ({page_id} < context.pages().length) {{",
					f"      const targetPage = context.pages()[{page_id}];",
					"      await targetPage.close();",
					"      await page.waitForTimeout(500);",
					"      if (context.pages().length > 0) page = context.pages()[context.pages().length - 1];",
					"      else {",
					"        console.log('  Warning: No pages left after closing tab. Cannot switch.');",
					"        // Optionally, create a new page here if needed: page = await context.newPage();",
					"      }",
					"      if (page) await page.bringToFront();",
					"    } else {",
					f"      console.log(`  Warning: Tab with page_id {page_id} not found to close ({step_info_str})`);",
					"    }",
				]
			)
		else:
			script_lines.append(f"    // Skipping close_tab ({step_info_str}): missing page_id")
		return script_lines

	def _map_switch_tab(self, params: dict, step_info_str: str, **kwargs) -> list[str]:
		page_id = params.get('page_id')
		script_lines = []
		if page_id is not None:
			script_lines.extend(
				[
					f"    console.log(`Switching to tab with page_id {page_id} ({step_info_str})`);",
					f"    if ({page_id} < context.pages().length) {{",
					f"      page = context.pages()[{page_id}];",
					"      await page.bringToFront();",
					"      await page.waitForLoadState('load', { timeout: 15000 });",
					"      await page.waitForTimeout(500);",
					"    } else {",
					f"      console.log(`  Warning: Tab with page_id {page_id} not found to switch ({step_info_str})`);",
					"    }",
				]
			)
		else:
			script_lines.append(f"    // Skipping switch_tab ({step_info_str}): missing page_id")
		return script_lines

	def _map_search_google(self, params: dict, step_info_str: str, **kwargs) -> list[str]:
		query = params.get('query')
		goto_timeout = self._get_goto_timeout()
		script_lines = []
		if query and isinstance(query, str):
			clean_query = f'replaceSensitiveData({json.dumps(query)}, SENSITIVE_DATA)'
			script_lines.extend(
				[
					f"    const cleanQuery = {clean_query};",
					f"    const searchUrl = `https://www.google.com/search?q=${{encodeURIComponent(cleanQuery)}}&udm=14`;",
					f"    console.log(`Searching Google for query related to: ${{cleanQuery}} ({step_info_str})`);",
					f"    await page.goto(searchUrl, {{ timeout: {goto_timeout} }});",
					f"    await page.waitForLoadState('load', {{ timeout: {goto_timeout} }});",
					"    await page.waitForTimeout(1000);",
				]
			)
		else:
			script_lines.append(f"    // Skipping search_google ({step_info_str}): missing or invalid query")
		return script_lines

	def _map_drag_drop(self, params: dict, step_info_str: str, **kwargs) -> list[str]:
		source_sel = params.get('element_source')
		target_sel = params.get('element_target')
		source_coords = (params.get('coord_source_x'), params.get('coord_source_y'))
		target_coords = (params.get('coord_target_x'), params.get('coord_target_y'))
		script_lines = [f"    console.log(`Attempting drag and drop ({step_info_str})`);"]
		if source_sel and target_sel:
			escaped_source = json.dumps(source_sel)
			escaped_target = json.dumps(target_sel)
			script_lines.append(f"    await page.dragAndDrop({escaped_source}, {escaped_target});")
			script_lines.append(f"    console.log(`  Dragged element {escaped_source} to {escaped_target}`);")
		elif all(c is not None for c in source_coords) and all(c is not None for c in target_coords):
			sx, sy = source_coords
			tx, ty = target_coords
			script_lines.extend(
				[
					f"    await page.mouse.move({sx}, {sy});",
					"    await page.mouse.down();",
					f"    await page.mouse.move({tx}, {ty});",
					"    await page.mouse.up();",
					f"    console.log(`  Dragged from ({sx},{sy}) to ({tx},{ty})`);",
				]
			)
		else:
			script_lines.append(
				f"    // Skipping drag_drop ({step_info_str}): requires either element selectors or full coordinates"
			)
		script_lines.append("    await page.waitForTimeout(500);")
		return script_lines

	def _map_extract_content(self, params: dict, step_info_str: str, **kwargs) -> list[str]:
		goal = params.get('goal', 'content')
		logger.warning(f"Action 'extract_content' ({step_info_str}) cannot be directly translated to Playwright script.")
		return [f"    // Action: extract_content (Goal: {goal}) - Skipped in Playwright script ({step_info_str})"]

	def _map_click_download_button(
		self, params: dict, history_item: dict, action_index_in_step: int, step_info_str: str, **kwargs
	) -> list[str]:
		index = params.get('index')
		selector = self._get_selector_for_action(history_item, action_index_in_step)
		download_dir_in_script = "'./files'"  # Default
		if self.context_config and self.context_config.save_downloads_path:
			download_dir_in_script = json.dumps(self.context_config.save_downloads_path)

		script_lines = []
		if selector and index is not None:
			script_lines.append(
				f"    console.log(`Attempting to download file by clicking element ({selector}) ({step_info_str})`);"
			)
			script_lines.append("    try {")
			script_lines.append("      const [download] = await Promise.all([")
			script_lines.append("        page.waitForEvent('download', { timeout: 120000 }),")
			step_info_for_download = f'{step_info_str} (triggering download)'
			script_lines.append(
				f"        tryLocateAndAct(page, {json.dumps(selector)}, 'click', null, {json.dumps(step_info_for_download)})"
			)
			script_lines.append("      ]);")
			script_lines.append(f"      const configuredDownloadDir = {download_dir_in_script};")
			script_lines.append("      const downloadDirPath = path.resolve(configuredDownloadDir);")
			script_lines.append("      if (!fs.existsSync(downloadDirPath)) fs.mkdirSync(downloadDirPath, { recursive: true });")
			script_lines.append(
				"      const suggestedFilename = download.suggestedFilename() || `download_${Date.now()}.tmp`;"
			)
			script_lines.append("      const ext = path.extname(suggestedFilename);")
			script_lines.append("      const base = path.basename(suggestedFilename, ext);")
			script_lines.append("      let counter = 1;")
			script_lines.append("      let downloadPath = path.join(downloadDirPath, `${base}${ext}`);")
			script_lines.append("      while (fs.existsSync(downloadPath)) {")
			script_lines.append("        downloadPath = path.join(downloadDirPath, `${base}(${counter})${ext}`);")
			script_lines.append("        counter++;")
			script_lines.append("      }")
			script_lines.append("      await download.saveAs(downloadPath);")
			script_lines.append("      console.log(`  File downloaded successfully to: ${downloadPath}`);")
			script_lines.append("    } catch (downloadErr) {")
			script_lines.append(
				f"      throw new PlaywrightActionError(`Download failed for {step_info_str}: ${{downloadErr}}`);"
			)
			script_lines.append("    }")
		else:
			script_lines.append(
				f"    // Skipping click_download_button ({step_info_str}): missing index ({index}) or selector ({selector})"
			)
		return script_lines

	def _map_done(self, params: dict, step_info_str: str, **kwargs) -> list[str]:
		script_lines = []
		if isinstance(params, dict):
			final_text = params.get('text', '')
			success_status = params.get('success', False)
			escaped_final_text_with_placeholders = json.dumps(str(final_text))
			script_lines.append(f"    console.log('\\n--- Task marked as Done by agent ({step_info_str}) ---');")
			script_lines.append(f"    console.log(`Agent reported success: {str(success_status).lower()}`);")
			script_lines.append("    // Final Message from agent (may contain placeholders):")
			script_lines.append(
				f"    const finalMessage = replaceSensitiveData({escaped_final_text_with_placeholders}, SENSITIVE_DATA);"
			)
			script_lines.append("    console.log(finalMessage);")
		else:
			script_lines.append(f"    console.log('\\n--- Task marked as Done by agent ({step_info_str}) ---');")
			script_lines.append("    console.log('Success: N/A (invalid params)');")
			script_lines.append("    console.log('Final Message: N/A (invalid params)');")
		return script_lines

	def _map_action_to_playwright(
		self,
		action_dict: dict,
		history_item: dict,
		previous_history_item: dict | None,
		action_index_in_step: int,
		step_info_str: str,
	) -> list[str]:
		"""
		Translates a single action dictionary into Playwright script lines using dictionary dispatch.
		"""
		if not isinstance(action_dict, dict) or not action_dict:
			return [f"    // Invalid action format: {action_dict} ({step_info_str})"]

		action_type = next(iter(action_dict.keys()), None)
		params = action_dict.get(action_type)

		if not action_type or params is None:
			if action_dict == {}:
				return [f"    // Empty action dictionary found ({step_info_str})"]
			return [f"    // Could not determine action type or params: {action_dict} ({step_info_str})"]

		# Get the handler function from the dictionary
		handler = self._action_handlers.get(action_type)

		if handler:
			# Call the specific handler method
			return handler(
				params=params,
				history_item=history_item,
				action_index_in_step=action_index_in_step,
				step_info_str=step_info_str,
				action_type=action_type,  # Pass action_type for legacy handling etc.
				previous_history_item=previous_history_item,
			)
		else:
			# Handle unsupported actions
			logger.warning(f'Unsupported action type encountered: {action_type} ({step_info_str})')
			return [f"    // Unsupported action type: {action_type} ({step_info_str})"]

	def generate_script_content(self) -> str:
		"""Generates the full JavaScript Playwright script content as a string."""
		script_lines = []
		self._page_counter = 0  # Reset page counter for new script generation

		script_lines.extend(self._get_imports_and_setup())
		script_lines.extend(self._get_helper_functions())

		# Generate browser launch and context creation code
		browser_launch_args = self._generate_browser_launch_args()
		context_options = self._generate_context_options()
		# Determine browser type (defaulting to chromium)
		browser_type = 'chromium'
		if self.browser_config and self.browser_config.browser_class in ['firefox', 'webkit']:
			browser_type = self.browser_config.browser_class

		script_lines.extend(
			[
				"async function runGeneratedScript() {",
				"  let browser = null;",
				"  let context = null;",
				"  let page = null;",
				"  let exitCode = 0; // Default success exit code",
				"  try {",
				f"    console.log('Launching {browser_type} browser...');",
				f"    browser = await {browser_type}.launch({browser_launch_args});",
				f"    context = await browser.newContext({context_options});",
				"    console.log('Browser context created.');",
			]
		)

		# Add cookie loading logic if cookies_file is specified
		if self.context_config and self.context_config.cookies_file:
			cookies_file_path = json.dumps(self.context_config.cookies_file)
			script_lines.extend(
				[
					"    // Load cookies if specified",
					f"    const cookiesPath = {cookies_file_path};",
					"    if (cookiesPath && fs.existsSync(cookiesPath)) {",
					"      try {",
					"        const cookiesData = fs.readFileSync(cookiesPath, 'utf-8');",
					"        const cookies = JSON.parse(cookiesData);",
					"        // Validate sameSite attribute",
					"        const validSameSite = ['Strict', 'Lax', 'None'];",
					"        for (const cookie of cookies) {",
					"          if (cookie.sameSite && !validSameSite.includes(cookie.sameSite)) {",
					"            console.log(`  Warning: Fixing invalid sameSite value \"${cookie.sameSite}\" to None for cookie ${cookie.name}`);",
					"            cookie.sameSite = 'None';",
					"          }",
					"        }",
					"        await context.addCookies(cookies);",
					"        console.log(`  Successfully loaded ${cookies.length} cookies from ${cookiesPath}`);",
					"      } catch (cookieErr) {",
					"        console.log(`  Warning: Failed to load or add cookies from ${cookiesPath}: ${cookieErr}`);",
					"      }",
					"    } else {",
					"      if (cookiesPath) {",
					"        console.log(`  Cookie file not found at: ${cookiesPath}`);",
					"      }",
					"    }",
					"",
				]
			)
		script_lines.extend(
			[
				"    // Initial page handling",
				"    if (context.pages().length > 0) {",
				"      page = context.pages()[0];",
				"      console.log('Using initial page provided by context.');",
				"    } else {",
				"      page = await context.newPage();",
				"      console.log('Created a new page as none existed.');",
				"    }",
				"",
				"    // Wait 15 seconds for manual captcha solving",
				"    console.log('⏱️  Waiting 15 seconds for manual captcha solving...');",
				"    await new Promise(resolve => setTimeout(resolve, 15000));",
				"    console.log('✅  15-second wait completed, continuing with automation');",
				"    console.log('\\n--- Starting Generated Script Execution ---');",
			]
		)

		action_counter = 0
		stop_processing_steps = False
		previous_item_dict = None

		for step_index, item_dict in enumerate(self.history):
			if stop_processing_steps:
				break

			if not isinstance(item_dict, dict):
				logger.warning(f'Skipping step {step_index + 1}: Item is not a dictionary ({type(item_dict)})')
				script_lines.append(f'\n    // --- Step {step_index + 1}: Skipped (Invalid Format) ---')
				previous_item_dict = item_dict
				continue

			script_lines.append(f'\n    // --- Step {step_index + 1} ---')
			model_output = item_dict.get('model_output')

			if not isinstance(model_output, dict) or 'action' not in model_output:
				script_lines.append('    // No valid model_output or action found for this step')
				previous_item_dict = item_dict
				continue

			actions = model_output.get('action')
			if not isinstance(actions, list):
				script_lines.append(f'    // Actions format is not a list: {type(actions)}')
				previous_item_dict = item_dict
				continue

			for action_index_in_step, action_detail in enumerate(actions):
				action_counter += 1
				script_lines.append(f'    // Action {action_counter}')

				step_info_str = f'Step {step_index + 1}, Action {action_index_in_step + 1}'
				action_lines = self._map_action_to_playwright(
					action_dict=action_detail,
					history_item=item_dict,
					previous_history_item=previous_item_dict,
					action_index_in_step=action_index_in_step,
					step_info_str=step_info_str,
				)
				script_lines.extend(action_lines)

				action_type = next(iter(action_detail.keys()), None) if isinstance(action_detail, dict) else None
				if action_type == 'done':
					stop_processing_steps = True
					break

			previous_item_dict = item_dict

		# Error handling and cleanup
		script_lines.extend(
			[
				"  } catch (pae) {",
				"    if (pae instanceof PlaywrightActionError) {",
				"      console.error(`\\n--- Playwright Action Error: ${pae.message} ---`);",
				"      exitCode = 1;",
				"    } else {",
				"      console.error(`\\n--- An unexpected error occurred: ${pae} ---`);",
				"      console.error(pae.stack);",
				"      exitCode = 1;",
				"    }",
				"  } finally {",
				"    console.log('\\n--- Generated Script Execution Finished ---');",
				"    console.log('Closing browser/context...');",
				"    if (context) {",
				"      try { await context.close(); }",
				"      catch (ctxCloseErr) { console.error(`  Warning: could not close context: ${ctxCloseErr}`); }",
				"    }",
				"    if (browser) {",
				"      try { await browser.close(); }",
				"      catch (browserCloseErr) { console.error(`  Warning: could not close browser: ${browserCloseErr}`); }",
				"    }",
				"    console.log('Browser/context closed.');",
				"    if (exitCode !== 0) {",
				"      console.error(`Script finished with errors (exit code ${exitCode}).`);",
				"      process.exit(exitCode);",
				"    }",
				"  }",
				"}",
				"",
				"// Script Entry Point",
				"runGeneratedScript().catch(console.error);",
			]
		)

		return '\n'.join(script_lines)
