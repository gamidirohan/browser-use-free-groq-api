import asyncio
import os
import argparse
import subprocess
import time
import socket
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from pydantic import SecretStr

from browser_use import Agent, Browser, BrowserConfig

# Default Chrome debugging port
DEFAULT_CHROME_DEBUG_PORT = 9222

# Load environment variables from .env file
# Explicitly specify the .env file path to ensure it's used instead of .env.example
import os
from pathlib import Path

# Get the absolute path to the .env file in the project root
env_path = Path(__file__).resolve().parent.parent / '.env'
print(f"Loading environment variables from: {env_path}")
load_dotenv(dotenv_path=env_path)

# Get DeepSeek API key from environment variables
deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
print(f"DeepSeek API Key found: {'Yes' if deepseek_api_key else 'No'}")

# Print all environment variables for debugging (masking sensitive values)
print("\nEnvironment variables loaded:")
for key in ["USER_EMAIL", "USER_NAME", "USER_LOCATION", "USER_EXPERIENCE", "USER_PHONE", "USER_LINKEDIN", "USER_GITHUB"]:
    value = os.getenv(key)
    if value:
        masked_value = value[:3] + "..." + value[-3:] if len(value) > 6 else "***"
        print(f"  {key}: {masked_value}")
    else:
        print(f"  {key}: Not found")

if not deepseek_api_key:
    raise ValueError("DEEPSEEK_API_KEY not found in environment variables. Please add it to your .env file.")

# Get sensitive data from environment variables or use defaults
sensitive_data = {}

# Define default values
default_values = {
    "email": "your_email@example.com",
    "password": "your_password",
    "name": "Your Name",
    "location": "India",
    "experience": "1 year or less",
    "phone": "+91 1234567890",
    "linkedin_url": "https://www.linkedin.com/in/your-profile/",
    "github_url": "https://github.com/yourusername",
}

# Populate sensitive_data with environment variables or defaults
for key, default in default_values.items():
    env_key = f"USER_{key.upper()}" if key != "linkedin_url" and key != "github_url" else f"USER_{'LINKEDIN' if key == 'linkedin_url' else 'GITHUB'}"
    value = os.getenv(env_key)
    sensitive_data[key] = value if value else default

print("\nSensitive data being used:")
for key in sensitive_data:
    if key == "password":
        print(f"  {key}: ********")
    else:
        value = sensitive_data[key]
        masked_value = value[:3] + "..." + value[-3:] if len(value) > 6 else "***"
        print(f"  {key}: {masked_value}")

def launch_chrome_with_debugging(chrome_path, debug_port=DEFAULT_CHROME_DEBUG_PORT, profile_mode=None):
    """Launch Chrome with remote debugging enabled"""
    try:
        # Check if Chrome is already running with debugging
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', debug_port))
        sock.close()

        if result == 0:
            print(f"Chrome already running with debugging on port {debug_port}")
            return True

        # Launch Chrome with debugging enabled
        print(f"Launching Chrome with remote debugging on port {debug_port}")

        # Verify the Chrome path exists
        if not os.path.exists(chrome_path):
            print(f"Chrome executable not found at: {chrome_path}")
            # Try to find Chrome in the default location
            default_path = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
            if os.path.exists(default_path):
                print(f"Using default Chrome path: {default_path}")
                chrome_path = default_path
            else:
                print("Could not find Chrome executable")
                return False

        # Check if Chrome is already running (without debugging)
        import psutil
        chrome_running = False
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and 'chrome' in proc.info['name'].lower():
                chrome_running = True
                break

        if chrome_running:
            print("Chrome is already running. Please close all Chrome instances before launching with debugging.")
            print("Alternatively, you can manually start Chrome with the --remote-debugging-port flag:")
            print(f"  {chrome_path} --remote-debugging-port={debug_port}")
            return False

        # Get the path to the default Chrome user data directory
        default_user_data_dir = os.path.expanduser("~") + "\\AppData\\Local\\Google\\Chrome\\User Data"

        # Create a copy of the default profile for debugging
        # This avoids the "profile in use" error while still preserving your logins
        debug_profile_dir = os.path.expanduser("~") + "\\AppData\\Local\\Temp\\Chrome-Debug-Profile"

        # Determine which profile to use
        if profile_mode == "default":
            # Use default profile directly
            user_data_dir = default_user_data_dir
            print("Using your default Chrome profile directly.")
        elif profile_mode == "copy":
            # Use a copy of the default profile
            user_data_dir = debug_profile_dir
            print(f"Using a copy of your profile at: {debug_profile_dir}")
        else:
            # Ask the user which profile to use
            print("\nChrome Profile Options:")
            print("1. Use a copy of your default profile (recommended)")
            print("2. Use your default profile directly (may cause 'profile in use' errors)")
            profile_choice = input("Enter your choice (1 or 2): ").strip()

            if profile_choice == "2":
                user_data_dir = default_user_data_dir
                print("Using your default Chrome profile directly.")
            else:
                user_data_dir = debug_profile_dir
                print(f"Using a copy of your profile at: {debug_profile_dir}")

        # If using a copy of the profile, make sure it exists
        if user_data_dir == debug_profile_dir:
            # Check if we need to create the debug profile
            if not os.path.exists(debug_profile_dir):
                print("Creating debug profile directory...")
                os.makedirs(debug_profile_dir, exist_ok=True)

                # Copy essential files from the default profile
                # This is a simplified approach - a full copy would be more complex
                try:
                    import shutil
                    # Copy Login Data to preserve logins
                    default_profile = os.path.join(default_user_data_dir, "Default")
                    debug_default_profile = os.path.join(debug_profile_dir, "Default")
                    os.makedirs(debug_default_profile, exist_ok=True)

                    # Copy key files if they exist
                    for file in ["Login Data", "Cookies", "Web Data", "Preferences"]:
                        src = os.path.join(default_profile, file)
                        dst = os.path.join(debug_default_profile, file)
                        if os.path.exists(src):
                            shutil.copy2(src, dst)
                            print(f"Copied {file} to debug profile")
                except Exception as e:
                    print(f"Error copying profile data: {e}")
                    print("Continuing with empty profile...")

        chrome_args = [
            chrome_path,
            f"--remote-debugging-port={debug_port}",
            "--no-first-run",
            "--no-default-browser-check",
            f"--user-data-dir={user_data_dir}"
        ]

        subprocess.Popen(chrome_args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Wait for Chrome to start
        print("Waiting for Chrome to start...")
        max_wait = 10  # seconds
        for i in range(max_wait):
            time.sleep(1)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', debug_port))
            sock.close()
            if result == 0:
                print(f"Successfully launched Chrome with debugging on port {debug_port}")
                return True
            print(f"Waiting... ({i+1}/{max_wait})")

        print(f"Failed to launch Chrome with debugging on port {debug_port}")
        return False
    except Exception as e:
        print(f"Error launching Chrome: {e}")
        return False

async def run_job_search(use_existing_browser=False, chrome_path="C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe", max_steps=100, profile_mode=None, use_memory=True):
    print("\n=== Job Search Configuration ===")
    if use_existing_browser:
        print(f"- Using existing Chrome browser with debugging on port {DEFAULT_CHROME_DEBUG_PORT}")
    else:
        print("- Launching new browser instance")
    print(f"- Maximum steps: {max_steps}")
    print("- Using DeepSeek API for language model")
    print(f"- Memory: {'Enabled' if use_memory else 'Disabled'}")

    # Configure browser
    browser_config_args = {
        "headless": False,  # Make browser visible
    }

    # If using existing browser, update config
    if use_existing_browser and chrome_path:
        print(f"Using existing Chrome browser at: {chrome_path}")

        # Launch Chrome with debugging if needed
        if launch_chrome_with_debugging(chrome_path, profile_mode=profile_mode):
            # Connect to the existing Chrome instance using CDP
            browser_config_args["cdp_url"] = f"http://localhost:{DEFAULT_CHROME_DEBUG_PORT}"
            print("Successfully configured to use existing Chrome browser with CDP")
        else:
            # If debugging fails, ask the user what to do
            print("\nFailed to connect to existing Chrome browser with debugging.")
            print("Options:")
            print("1. Continue with a new browser instance")
            print("2. Exit and try again after closing Chrome")
            choice = input("Enter your choice (1 or 2): ").strip()

            if choice == "2":
                print("Exiting. Please close all Chrome instances and try again.")
                return

            print("Continuing with a new browser instance...")

    # Create browser with config
    browser_config = BrowserConfig(**browser_config_args)
    browser = Browser(config=browser_config)

    try:
        # Create the agent with our custom task
        agent = Agent(
            task="""
            Find GRC (Governance, Risk, and Compliance) or GSRC jobs for {name} with:
            - Remote work from {location}
            - {experience} experience required
            - Currently accepting applications

            1. SEARCH LINKEDIN JOBS:
               • Go to https://www.linkedin.com/jobs/
               • Search for: "GRC OR GSRC OR Governance Risk Compliance"
               • Filter for remote work and entry level
               • Get 10 job listings (title, company, location, experience, link)

            2. SEARCH INDEED JOBS:
               • Go to https://www.indeed.com/
               • Search with same keywords and filters
               • Get additional listings to reach 15 total

            3. COMPILE RESULTS:
               • Create a numbered list of all jobs
               • Include essential details for each
               • Sort by relevance to {name}'s profile

            4. EXIT when done
            """,
            llm=ChatOpenAI(
                base_url='https://api.deepseek.com/v1',
                model='deepseek-chat',
                api_key=SecretStr(deepseek_api_key),
                temperature=0.2,  # Lower temperature for more focused responses
                max_tokens=4000,  # Limit response length to avoid context issues
            ),
            browser=browser,  # Use our configured browser
            use_vision=False,

            sensitive_data=sensitive_data,  # Protect your credentials
        )

        # Run the agent
        await agent.run(max_steps=max_steps)  # Allow enough steps for the complex workflow
    finally:
        # Close browser when done
        await browser.close()

if __name__ == '__main__':
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Run a job search automation task using DeepSeek API')
    parser.add_argument('--steps', type=int, default=100,
                        help='Maximum number of steps to run (default: 100)')
    parser.add_argument('--use-existing-browser', action='store_true',
                        help='Use existing Chrome browser instead of launching a new one')
    parser.add_argument('--chrome-path', type=str,
                        default="C:/Program Files/Google/Chrome/Application/chrome.exe",
                        help='Path to Chrome executable (default: standard Chrome installation path)')
    parser.add_argument('--profile-mode', type=str, choices=['default', 'copy'],
                        help='Chrome profile mode: "default" uses your regular profile, "copy" uses a copy of your profile')
    parser.add_argument('--no-memory', action='store_true',
                        help='Disable memory functionality to avoid context length issues')

    # Parse arguments
    args = parser.parse_args()

    # Run the job search with the specified arguments
    asyncio.run(run_job_search(
        use_existing_browser=args.use_existing_browser,
        chrome_path=args.chrome_path,
        max_steps=args.steps,
        profile_mode=args.profile_mode,
        use_memory=not args.no_memory  # Use memory unless --no-memory is specified
    ))