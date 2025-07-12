#!/usr/bin/env python3

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.abspath('.'))

from browser_use.agent.views import AgentHistoryList, ActionResult
from browser_use.agent.playwright_script_generator import PlaywrightScriptGenerator
from browser_use.agent.playwright_script_generator_js import PlaywrightScriptGeneratorJS
from browser_use.browser.browser import BrowserConfig
from browser_use.browser.context import BrowserContextConfig

def test_generated_scripts_include_wait():
    """Test that generated scripts include the 15-second captcha wait"""
    
    print("Starting script generation test...")
    
    # Create a minimal history with a simple navigation action
    history_data = [
        {
            'model_dump': lambda: {
                'result': {
                    'extracted_content': '',
                    'include_in_memory': True,
                    'screenshot': ''
                },
                'state': {
                    'url': 'https://www.google.com',
                    'title': 'Google'
                },
                'action': {
                    'action_type': 'go_to_url',
                    'params': {'url': 'https://www.google.com'}
                }
            }
        }
    ]
    
    print("Created test history data...")
    
    # Convert to model_dump format
    history_list = [item['model_dump']() for item in history_data]
    
    browser_config = BrowserConfig(headless=False)
    context_config = BrowserContextConfig()
    
    print("Created browser and context configs...")
    
    # Test Python script generation
    print("=== Testing Python Script Generation ===")
    python_generator = PlaywrightScriptGenerator(
        history_list=history_list,
        browser_config=browser_config,
        context_config=context_config
    )
    
    python_script = python_generator.generate_script_content()
      # Check if the wait is included
    if "Waiting 15 seconds for manual captcha solving" in python_script:
        print("✅ Python script includes 15-second wait")
    else:
        print("❌ Python script missing 15-second wait")
    
    if "await asyncio.sleep(15)" in python_script:
        print("✅ Python script includes asyncio.sleep(15)")
    else:
        print("❌ Python script missing asyncio.sleep(15)")
    
    # Test JavaScript script generation
    print("\n=== Testing JavaScript Script Generation ===")
    js_generator = PlaywrightScriptGeneratorJS(
        history_list=history_list,
        browser_config=browser_config,
        context_config=context_config
    )
    
    js_script = js_generator.generate_script_content()
    
    # Check if the wait is included
    if "Waiting 15 seconds for manual captcha solving" in js_script:
        print("✅ JavaScript script includes 15-second wait")
    else:
        print("❌ JavaScript script missing 15-second wait")
    
    if "setTimeout(resolve, 15000)" in js_script:
        print("✅ JavaScript script includes setTimeout(resolve, 15000)")
    else:
        print("❌ JavaScript script missing setTimeout(resolve, 15000)")
      # Write sample scripts to files for inspection
    with open('test_python_script_with_wait.py', 'w', encoding='utf-8') as f:
        f.write(python_script)
    
    with open('test_js_script_with_wait.js', 'w', encoding='utf-8') as f:
        f.write(js_script)
    
    print(f"\n📄 Sample scripts written to:")
    print(f"  - test_python_script_with_wait.py")
    print(f"  - test_js_script_with_wait.js")

if __name__ == '__main__':
    test_generated_scripts_include_wait()
