import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from browser_use import Agent

load_dotenv()

# Initialize the model
llm = ChatOpenAI(
	model='gpt-4o',
	temperature=0.0,
)
task = 'Go to github, look up "browser-use", and return the list of contributers with their contributions.'

agent = Agent(task=task, llm=llm, save_playwright_script_path="replay_script.py")


async def main():
    history = await agent.run()
    if history:
        history.save_to_file("agent_history.json")
        # Automatically generate flow.json for React Flow app
        import subprocess
        subprocess.run([sys.executable, "generate_flow_json.py"], check=True)


if __name__ == '__main__':
	asyncio.run(main())
