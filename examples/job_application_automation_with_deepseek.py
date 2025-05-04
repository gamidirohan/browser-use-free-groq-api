import asyncio
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from browser_use import Agent

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

async def run_job_search():
    agent = Agent(
        task="""
        Find and compile a list of the top 20 GRC (Governance, Risk, and Compliance) or GSRC job opportunities for {name} that:
        - Allow remote work from {location}
        - Require {experience} experience
        - Are currently accepting applications

        1. SEARCH LINKEDIN JOBS:
           • Go to https://www.linkedin.com/jobs/
           • Continue with Google and Enter Login Credentials
           • Search for keywords: ("GRC" OR "GSRC" OR "Governance Risk Compliance")
           • Filter for:
              - Remote or "Work from {location}"
              - Entry level or "1 year experience"
              - Posted in the last month
           • Extract the top 20 job listings with:
              - Company name
              - Job title
              - Location/Remote status
              - Experience requirements
              - Application link
              - Application deadline (if available)

        2. SEARCH INDEED JOBS:
           • Go to https://www.indeed.com/
           • Search for the same keywords and filters
           • Extract additional job listings to reach a total of 20 if needed

        3. SEARCH NAUKRI.COM:
           • Go to https://www.naukri.com/
           • Search for the same keywords and filters
           • Extract additional job listings to reach a total of 20 if needed

        4. COMPILE RESULTS:
           • Create a numbered list of all jobs found
           • For each job include:
              - Job title
              - Company name
              - Location/Remote status
              - Experience required
              - Application link
              - Brief job description (1-2 sentences)
           • Sort the list by most relevant to {name}'s profile

        5. EXIT when you have compiled a list of the top 20 jobs
        """,
        llm=ChatOpenAI(
            base_url='https://api.deepseek.com/v1',
            model='deepseek-chat',
            api_key=SecretStr(deepseek_api_key),
        ),
        use_vision=False,
        sensitive_data=sensitive_data,  # Protect your credentials
    )

    await agent.run(max_steps=100)  # Allow enough steps for the complex workflow

if __name__ == '__main__':
    asyncio.run(run_job_search())