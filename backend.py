from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import subprocess
import sys
import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime

# Import browser_use modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from browser_use import Agent
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Agent Flow API", version="1.0.0")

# Enable CORS for React app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TaskRequest(BaseModel):
    task: str
    model: str = "gpt-4o"
    temperature: float = 0.0
    script_language: str = "python"  # "python" or "javascript"

class RecordingRequest(BaseModel):
    name: str
    task: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    timestamp: str

class ScriptRegenerateRequest(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]

class AgentStatus(BaseModel):
    status: str  # "idle", "running", "completed", "error"
    message: str
    history_available: bool = False
    flow_available: bool = False
    replay_available: bool = False
    script_language: str = "python"  # Track which language was used

# Global status tracking
current_status = AgentStatus(status="idle", message="Ready to run agent", script_language="python")

# Recordings storage
RECORDINGS_DIR = Path("recordings")
RECORDINGS_DIR.mkdir(exist_ok=True)

def get_recordings_file():
    return RECORDINGS_DIR / "recordings.json"

def load_recordings():
    recordings_file = get_recordings_file()
    if recordings_file.exists():
        with open(recordings_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_recordings(recordings):
    recordings_file = get_recordings_file()
    with open(recordings_file, 'w', encoding='utf-8') as f:
        json.dump(recordings, f, indent=2, ensure_ascii=False)

@app.get("/")
async def root():
    return {"message": "Agent Flow API is running"}

@app.get("/status")
async def get_status():
    return current_status

@app.post("/run-agent")
async def run_agent(request: TaskRequest):
    global current_status
    
    try:
        current_status.status = "running"
        current_status.message = f"Running agent with task: {request.task[:50]}..."
        
        # Initialize the model
        llm = ChatOpenAI(
            model=request.model,
            temperature=request.temperature,
        )
        
        # Determine script file extension and language
        script_extension = ".js" if request.script_language == "javascript" else ".py"
        script_filename = f"replay_script{script_extension}"
        
        # Create agent
        agent = Agent(
            task=request.task, 
            llm=llm, 
            save_playwright_script_path=script_filename,
            playwright_script_language=request.script_language
        )
        
        # Run agent
        history = await agent.run()
        
        # Update global status with script language
        current_status.script_language = request.script_language
        
        # Save history
        if history:
            history.save_to_file("agent_history.json")
            current_status.history_available = True
            
            # Automatically generate flow.json
            subprocess.run([sys.executable, "generate_flow_json.py"], check=True)
            current_status.flow_available = True
            current_status.replay_available = True
            
        current_status.status = "completed"
        current_status.message = "Agent completed successfully"
        
        return {
            "success": True, 
            "message": "Agent completed successfully",
            "final_result": history.final_result() if history else None,
            "script_language": request.script_language,
            "script_file": script_filename
        }
        
    except Exception as e:
        current_status.status = "error"
        current_status.message = f"Error: {str(e)}"
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-flow")
async def generate_flow():
    try:
        if not Path("agent_history.json").exists():
            raise HTTPException(status_code=400, detail="No agent history found. Run agent first.")
            
        subprocess.run([sys.executable, "generate_flow_json.py"], check=True)
        current_status.flow_available = True
        
        return {"success": True, "message": "Flow generated successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run-replay")
async def run_replay():
    try:
        # Determine which script file to run based on current status
        script_extension = ".js" if current_status.script_language == "javascript" else ".py"
        script_filename = f"replay_script{script_extension}"
        
        if not Path(script_filename).exists():
            raise HTTPException(status_code=400, detail=f"No replay script found ({script_filename}). Run agent first.")
        
        # Run replay script in background
        if current_status.script_language == "javascript":
            # Run JavaScript script with Node.js
            process = subprocess.Popen(["node", script_filename])
        else:
            # Run Python script
            process = subprocess.Popen([sys.executable, script_filename])
        
        return {
            "success": True, 
            "message": f"Replay script started ({script_filename})",
            "process_id": process.pid,
            "script_language": current_status.script_language
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/flow-data")
async def get_flow_data():
    try:
        flow_path = Path("agent-flow-visualizer/public/flow.json")
        if not flow_path.exists():
            return {"nodes": [], "edges": []}
            
        with open(flow_path) as f:
            return json.load(f)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/recordings")
async def get_recordings():
    """Get all saved recordings"""
    try:
        recordings = load_recordings()
        return recordings
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/recordings")
async def save_recording(request: RecordingRequest):
    """Save a new recording"""
    try:
        recordings = load_recordings()
        
        # Create new recording
        new_recording = {
            "id": str(uuid.uuid4()),
            "name": request.name,
            "task": request.task,
            "nodes": request.nodes,
            "edges": request.edges,
            "timestamp": request.timestamp,
            "created_at": datetime.now().isoformat()
        }
        
        recordings.append(new_recording)
        save_recordings(recordings)
        
        return {"success": True, "message": "Recording saved successfully", "id": new_recording["id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/recordings/{recording_id}")
async def get_recording(recording_id: str):
    """Get a specific recording by ID"""
    try:
        recordings = load_recordings()
        recording = next((r for r in recordings if r["id"] == recording_id), None)
        
        if not recording:
            raise HTTPException(status_code=404, detail="Recording not found")
            
        return recording
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/recordings/{recording_id}")
async def delete_recording(recording_id: str):
    """Delete a recording by ID"""
    try:
        recordings = load_recordings()
        original_count = len(recordings)
        recordings = [r for r in recordings if r["id"] != recording_id]
        
        if len(recordings) == original_count:
            raise HTTPException(status_code=404, detail="Recording not found")
            
        save_recordings(recordings)
        return {"success": True, "message": "Recording deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/regenerate-script")
async def regenerate_script(request: ScriptRegenerateRequest):
    """Regenerate script from manually edited flow"""
    try:
        # Import the script generation functions
        from browser_use.agent.playwright_script_generator import generate_playwright_script
        from browser_use.agent.playwright_script_generator_js import generate_playwright_script_js
        
        # Convert nodes back to action format for script generation
        actions = []
        for node in request.nodes:
            if 'actionType' in node.get('data', {}):
                action_type = node['data']['actionType']
                action_params = node['data'].get('actionParams', {})
                actions.append({action_type: action_params})
        
        # Generate Python script
        python_script = generate_playwright_script(actions, "Manually edited flow")
        with open("replay_script.py", 'w', encoding='utf-8') as f:
            f.write(python_script)
        
        # Generate JavaScript script
        js_script = generate_playwright_script_js(actions, "Manually edited flow")
        with open("replay_script.js", 'w', encoding='utf-8') as f:
            f.write(js_script)
        
        # Update status
        global current_status
        current_status.replay_available = True
        
        return {"success": True, "message": "Scripts regenerated successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/script-info")
async def get_script_info():
    """Get information about available replay scripts"""
    try:
        scripts = []
        
        # Check for Python script
        if Path("replay_script.py").exists():
            scripts.append({
                "filename": "replay_script.py",
                "language": "python",
                "exists": True
            })
        
        # Check for JavaScript script
        if Path("replay_script.js").exists():
            scripts.append({
                "filename": "replay_script.js", 
                "language": "javascript",
                "exists": True
            })
        
        return {
            "current_language": current_status.script_language,
            "available_scripts": scripts
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
