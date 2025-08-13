from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
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
import logging
import re

# Import browser_use modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from browser_use import Agent
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Agent Flow API", version="1.0.0")

# WebSocket Connection Manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

manager = ConnectionManager()

# Enable CORS for all origins (development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TaskRequest(BaseModel):
    task: str
    model: str = "gpt-4o"
    temperature: float = 0.0
    script_language: str = "python"  # "python" or "javascript"
    # New: optionally save this run as a recording
    save_recording: bool = False
    recording_name: Optional[str] = None

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
    status: str  # "idle", "running", "completed", "error", "debugging", "paused"
    message: str
    history_available: bool = False
    flow_available: bool = False
    replay_available: bool = False
    script_language: str = "python"  # Track which language was used

class DebugRequest(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    breakpoints: List[str] = []  # Node IDs where to break
    mode: str = "run"  # "run", "step", "pause", "resume", "stop"

class DebugState(BaseModel):
    is_debugging: bool = False
    current_node: Optional[str] = None
    breakpoints: List[str] = []
    mode: str = "stopped"  # "running", "paused", "stopped", "stepping"
    execution_history: List[Dict[str, Any]] = []

# Global status tracking
current_status = AgentStatus(status="idle", message="Ready to run agent", script_language="python")
debug_state = DebugState()

# Debug execution engine
class DebugExecutor:
    def __init__(self):
        self.current_node_index = 0
        self.execution_flow = []
        self.is_running = False
        self.agent = None
        self.browser_context = None

    def _infer_action_from_label(self, label: str) -> tuple[str, dict]:
        """Infer an actionType and params from a node label string.
        Supports: navigate (Open New Tab ...), wait, scroll, press_key, input text (with optional Index and Text),
        click by index, select dropdown option, extract content, noop.
        """
        try:
            if not label:
                return "unknown", {}
            parts = [p.strip() for p in str(label).split("\n") if p.strip()]
            head = parts[0].lower()

            # Open New Tab -> navigate URL on second line
            if head.startswith("open new tab") and len(parts) > 1:
                return "navigate", {"url": parts[1]}

            # Wait -> e.g., "Wait", second line "5 seconds" or same line
            if head.startswith("wait"):
                text = " ".join(parts[1:]) if len(parts) > 1 else label
                m = re.search(r"(\d+(?:\.\d+)?)\s*sec", text, re.I)
                secs = float(m.group(1)) if m else 1.0
                return "wait", {"duration": secs}

            # Scroll Down/Up
            if head.startswith("scroll down"):
                return "scroll", {"dx": 0, "dy": 800}
            if head.startswith("scroll up"):
                return "scroll", {"dx": 0, "dy": -800}

            # Send Keys
            if head.startswith("send keys"):
                # Example: second line "Keys: Enter"
                key_line = next((p for p in parts if p.lower().startswith("keys:")), None)
                key = key_line.split(":", 1)[1].strip() if key_line and ":" in key_line else "Enter"
                return "press_key", {"key": key}

            # Input Text (optionally with index)
            if head.startswith("input text"):
                text_line = next((p for p in parts if p.lower().startswith("text:")), None)
                idx_line = next((p for p in parts if p.lower().startswith("index:")), None)
                text_val = ""
                if text_line and ":" in text_line:
                    text_val = text_line.split(":", 1)[1].strip().strip('"')
                if idx_line and re.search(r"\d+", idx_line):
                    idx = int(re.search(r"\d+", idx_line).group(0)) - 1
                    return "type_text_input_by_index", {"index": max(0, idx), "text": text_val}
                return "type_text_active", {"text": text_val}

            # Click Element By Index (handles variations like "Click Element By Index Step X.Y")
            if head.startswith("click element by index"):
                # Try to find "Index: N" in any line
                idx_line = next((p for p in parts if p.lower().startswith("index:")), None)
                if idx_line and re.search(r"\d+", idx_line):
                    idx = int(re.search(r"\d+", idx_line).group(0)) - 1
                else:
                    # Best effort: look for any number in the label after the head
                    m = re.search(r"index\s*[:#-]?\s*(\d+)", label, re.I)
                    idx = int(m.group(1)) - 1 if m else 0
                return "click_by_index", {"index": max(0, idx)}

            # Select Dropdown Option
            if head.startswith("select dropdown option") or head.startswith("select option"):
                # Support lines like "Index: N" for select element, and "Option: X" (text or number)
                idx_line = next((p for p in parts if p.lower().startswith("index:")), None)
                opt_line = next((p for p in parts if p.lower().startswith("option:")), None)
                element_index = None
                option_index = None
                option_text = None
                if idx_line and re.search(r"\d+", idx_line):
                    element_index = max(0, int(re.search(r"\d+", idx_line).group(0)) - 1)
                if opt_line and ":" in opt_line:
                    opt_val = opt_line.split(":", 1)[1].strip().strip('"')
                    if re.fullmatch(r"\d+", opt_val):
                        option_index = max(0, int(opt_val) - 1)
                    else:
                        option_text = opt_val
                return "select_option", {"element_index": element_index, "option_index": option_index, "option_text": option_text}

            # Extract Content -> let agent handle
            if head.startswith("extract content"):
                return "agent_instruction", {"instruction": label}

            # Done -> no-op
            if head.startswith("done"):
                return "noop", {}
        except Exception:
            pass
        return "agent_instruction", {"instruction": label}

    async def prepare_execution(self, nodes, edges, breakpoints):
        """Prepare the execution flow from nodes and edges"""
        # Sort nodes by execution order (simplified - assumes linear flow)
        self.execution_flow = sorted(nodes, key=lambda x: x.get('position', {}).get('y', 0))
        debug_state.breakpoints = breakpoints
        debug_state.execution_history = []
        self.current_node_index = 0
        # Initialize browser for debug session
        try:
            llm = ChatOpenAI(
                model="gpt-4o",
                temperature=0.0,
                api_key=os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY"),
                base_url=os.getenv("GROQ_BASE_URL") if os.getenv("GROQ_API_KEY") else None
            )

            self.agent = Agent(
                task="Debug execution - browser automation",
                llm=llm,
                use_vision=True,
                save_conversation_path="agent_debug_history.json"
            )

            # CRITICAL: Start the browser session immediately
            logger.info("Starting browser session for debug mode...")
            # Ensure headful mode so a visible window opens
            self.agent.browser.config.headless = False
            # For debug sessions, disable captcha wait to speed up startup
            os.environ.setdefault("BROWSER_USE_CAPTCHA_WAIT_SECONDS", "0")
            # Initialize the Playwright browser process
            await self.agent.browser.get_playwright_browser()
            # Force-create a browser context and page so the window appears now
            await self.agent.browser_context.get_current_page()
            logger.info("Debug browser session started successfully")

        except Exception as e:
            logger.error(f"Failed to initialize debug agent: {e}")
            raise

        await self._update_debug_state("prepared", "Debug session prepared with browser")

    async def execute_next_step(self):
        """Execute the next step in the flow"""
        if self.current_node_index >= len(self.execution_flow):
            await self._finish_execution()
            return False

        current_node = self.execution_flow[self.current_node_index]
        node_id = current_node['id']
        node_data = current_node.get('data', {})
        action_type = node_data.get('actionType', 'unknown')

        # Update current node
        debug_state.current_node = node_id

        # Log execution
        debug_state.execution_history.append({
            "timestamp": datetime.now().isoformat(),
            "node_id": node_id,
            "action_type": action_type,
            "message": f"Executing {node_data.get('label', 'Unknown')}"
        })

        await self._update_debug_state("running", f"Executing node: {node_data.get('label', 'Unknown')}")

        # Execute the actual browser action if agent is available
        if self.agent:
            try:
                await self._execute_browser_action(current_node)
            except Exception as e:
                logger.error(f"Error executing browser action: {e}")
                debug_state.execution_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "node_id": node_id,
                    "message": f"Error: {str(e)}",
                    "error": True
                })
        else:
            # Fallback: simulate execution
            await asyncio.sleep(1)

        # Check if this is a breakpoint
        if node_id in debug_state.breakpoints:
            debug_state.mode = "paused"
            await self._update_debug_state("paused", f"Paused at breakpoint: {node_data.get('label', 'Unknown')}")
            return True  # Paused at breakpoint
        # Move to next node
        self.current_node_index += 1
        return True  # Continue execution

    async def _execute_browser_action(self, node):
        """Execute the actual browser action for a node"""
        node_data = node.get('data', {})
        action_type = node_data.get('actionType', 'unknown')
        action_params = node_data.get('actionParams', {})

        if not self.agent:
            logger.warning("No agent available for browser action execution")
            await asyncio.sleep(0.5)
            return
        try:
            # Use the browser directly since it's already started
            page = await self.agent.browser_context.get_current_page()

            # If unknown, try to infer from label or fallback to agent instruction
            if action_type == 'unknown':
                inferred_type, inferred_params = self._infer_action_from_label(node_data.get('label', ''))
                action_type = inferred_type
                action_params = {**inferred_params, **action_params}

            if action_type == 'click_element':
                selector = action_params.get('selector')
                if selector:
                    logger.info(f"Debug: Clicking element with selector: {selector}")
                    await page.click(selector)
                    logger.info(f"Successfully clicked element: {selector}")
                else:
                    logger.info("Debug: No selector provided, falling back to agent click")
                    await self.agent.run("Click on the first clickable element on the page")

            elif action_type == 'click_by_index':
                idx = int(action_params.get('index', 0))
                locator = page.locator('a, button, [role="button"], input[type="submit"], [tabindex]')
                count = await locator.count()
                if count == 0:
                    logger.info("No clickable elements found, falling back to agent click")
                    await self.agent.run("Click on the first clickable element on the page")
                else:
                    i = max(0, min(idx, count - 1))
                    logger.info(f"Debug: Clicking element at index {i} from generic clickable locator")
                    await locator.nth(i).scroll_into_view_if_needed()
                    await locator.nth(i).click()

            elif action_type == 'type_text':
                text = action_params.get('text')
                selector = action_params.get('selector')
                if text and selector:
                    logger.info(f"Debug: Typing '{text}' into element: {selector}")
                    await page.fill(selector, text)
                    logger.info(f"Successfully typed text into: {selector}")
                elif text:
                    logger.info(f"Debug: No selector provided, falling back to active-field typing of '{text}'")
                    await page.keyboard.type(text)
                else:
                    logger.info("Debug: Missing text for type_text, skipping")

            elif action_type == 'type_text_active':
                text = action_params.get('text', '')
                if text:
                    logger.info(f"Debug: Typing into active element: '{text}'")
                    await page.keyboard.type(text)
                else:
                    logger.info("Debug: No text provided for type_text_active, skipping")

            elif action_type == 'type_text_input_by_index':
                text = action_params.get('text', '')
                idx = int(action_params.get('index', 0))
                inputs = page.locator('input, textarea, [contenteditable="true"]')
                count = await inputs.count()
                if count == 0:
                    logger.info("No input elements found; falling back to typing into active element")
                    if text:
                        await page.keyboard.type(text)
                else:
                    i = max(0, min(idx, count - 1))
                    target = inputs.nth(i)
                    await target.scroll_into_view_if_needed()
                    await target.click()
                    if text:
                        await target.fill("")
                        await target.type(text)

            elif action_type == 'press_key':
                key = action_params.get('key', 'Enter')
                logger.info(f"Debug: Pressing key: {key}")
                await page.keyboard.press(key)

            elif action_type == 'navigate':
                url = action_params.get('url')
                if url:
                    logger.info(f"Debug: Navigating to: {url}")
                    await page.goto(url)
                    logger.info(f"Successfully navigated to: {url}")
                else:
                    logger.info("Debug: No URL provided for navigate, skipping")

            elif action_type == 'scroll':
                dx = int(action_params.get('dx', 0))
                dy = int(action_params.get('dy', 800))
                logger.info(f"Debug: Scrolling by ({dx}, {dy})")
                await page.mouse.wheel(dx, dy)

            elif action_type == 'wait':
                duration = action_params.get('duration', 1)
                logger.info(f"Debug: Waiting for {duration} seconds")
                await asyncio.sleep(float(duration))

            elif action_type == 'select_option':
                element_index = action_params.get('element_index')
                option_index = action_params.get('option_index')
                option_text = action_params.get('option_text')
                selects = page.locator('select')
                count = await selects.count()
                if count == 0:
                    logger.info("No <select> elements found; delegating to agent")
                    await self.agent.run(node_data.get('label') or 'Select the described dropdown option')
                else:
                    i = 0 if element_index is None else max(0, min(int(element_index), count - 1))
                    target = selects.nth(i)
                    await target.scroll_into_view_if_needed()
                    if option_index is not None:
                        await target.select_option(index=int(option_index))
                    elif option_text:
                        await target.select_option(label=str(option_text))
                    else:
                        # default to first option after the placeholder
                        await target.select_option(index=1 if await target.evaluate('(el)=>el.options.length>1') else 0)

            elif action_type == 'agent_instruction':
                instr = action_params.get('instruction') or node_data.get('label') or 'Proceed with the described step'
                logger.info(f"Debug: Delegating to agent with instruction: {instr}")
                await self.agent.run(instr)

            elif action_type == 'noop':
                logger.info("Debug: No operation for this node")

            else:
                logger.info(f"Debug: Unknown action '{action_type}', skipping")

        except Exception as e:
            logger.error(f"Error executing browser action {action_type}: {e}")

        # Small delay between actions for stability
        await asyncio.sleep(0.5)

    async def _finish_execution(self):
        """Finish the debug execution"""
        debug_state.is_debugging = False
        debug_state.current_node = None
        debug_state.mode = "stopped"
        global current_status
        current_status.status = "completed"

        # Clean up browser resources
        if self.agent:
            try:
                await self.agent.browser_context.close()
            except Exception:
                pass
            try:
                await self.agent.browser.close()
            except Exception:
                pass

        await self._update_debug_state("completed", "Debug execution completed")

    async def _update_debug_state(self, status, message):
        """Update debug state and broadcast"""
        debug_state.mode = status
        current_status.message = message
        await broadcast_debug_update()
        await broadcast_status_update()

# Ensure only a single instance exists
debug_executor = DebugExecutor()

# Event broadcasting helper
async def broadcast_status_update():
    """Broadcast current status to all connected clients"""
    await manager.broadcast({
        "type": "status_update",
        "data": current_status.model_dump()
    })

async def broadcast_flow_update():
    """Broadcast flow data update to all connected clients"""
    try:
        flow_path = Path("agent-flow-visualizer/public/flow.json")
        if flow_path.exists():
            with open(flow_path) as f:
                flow_data = json.load(f)
            await manager.broadcast({
                "type": "flow_update",
                "data": flow_data
            })
    except Exception as e:
        logger.error(f"Error broadcasting flow update: {e}")

async def broadcast_recordings_update():
    """Broadcast recordings update to all connected clients"""
    try:
        recordings = load_recordings()
        await manager.broadcast({
            "type": "recordings_update",
            "data": recordings
        })
    except Exception as e:
        logger.error(f"Error broadcasting recordings update: {e}")

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

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Prepare initial flow data if available
        flow_payload = None
        flow_path = Path("agent-flow-visualizer/public/flow.json")
        if flow_path.exists():
            try:
                with open(flow_path, encoding="utf-8") as f:
                    flow_payload = json.load(f)
            except Exception as e:
                logger.error(f"Failed to read initial flow data: {e}")
        
        # Send initial data when client connects (status, recordings, optional flow)
        await websocket.send_text(json.dumps({
            "type": "initial_data",
            "data": {
                "status": current_status.model_dump(),
                "recordings": load_recordings(),
                **({"flow_data": flow_payload} if flow_payload else {})
            }
        }))
        
        # Also send a flow_update message to keep legacy handlers working
        if flow_payload:
            await websocket.send_text(json.dumps({
                "type": "flow_update",
                "data": flow_payload
            }))
        
        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            # Handle client messages if needed
            logger.info(f"Received WebSocket message: {data}")
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@app.get("/status")
async def get_status():
    return current_status

@app.post("/run-agent")
async def run_agent(request: TaskRequest):
    global current_status
    
    try:
        current_status.status = "running"
        current_status.message = f"Running agent with task: {request.task[:50]}..."
        await broadcast_status_update()
        
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
            
            # Broadcast flow update so UI can show live flow after completion
            await broadcast_flow_update()

            # Optionally save this task/run as a recording
            if request.save_recording:
                try:
                    flow_path = Path("agent-flow-visualizer/public/flow.json")
                    nodes, edges = [], []
                    if flow_path.exists():
                        with open(flow_path, encoding="utf-8") as f:
                            flow = json.load(f)
                            nodes = flow.get("nodes", [])
                            edges = flow.get("edges", [])
                    recordings = load_recordings()
                    new_rec = {
                        "id": str(uuid.uuid4()),
                        "name": request.recording_name or (request.task[:40] + ("..." if len(request.task) > 40 else "")),
                        "task": request.task,
                        "nodes": nodes,
                        "edges": edges,
                        "timestamp": datetime.now().isoformat(),
                        "created_at": datetime.now().isoformat(),
                    }
                    recordings.append(new_rec)
                    save_recordings(recordings)
                    # Notify clients to refresh recordings list
                    await broadcast_recordings_update()
                except Exception as e:
                    logger.error(f"Failed to save recording: {e}")
        
        current_status.status = "completed"
        current_status.message = "Agent completed successfully"
        await broadcast_status_update()
        
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
        await broadcast_status_update()
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
        
        # Broadcast recordings update
        await broadcast_recordings_update()
        
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
        
        # Broadcast recordings update
        await broadcast_recordings_update()
        
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
        await broadcast_status_update()
        
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

@app.post("/debug/start")
async def start_debug_session(request: DebugRequest):
    """Start a debugging session with breakpoints"""
    try:
        global debug_state, current_status, debug_executor
        
        debug_state.is_debugging = True
        debug_state.breakpoints = request.breakpoints
        # Normalize mode to internal states used by the loop
        if request.mode == "run":
            debug_state.mode = "running"
        elif request.mode == "step":
            debug_state.mode = "stepping"
        else:
            debug_state.mode = request.mode  # fallback
        debug_state.current_node = None
        debug_state.execution_history = []
        
        current_status.status = "debugging"
        current_status.message = f"Debug session started with {len(request.breakpoints)} breakpoints"
        
        # Prepare the debug executor (opens Chromium immediately)
        await debug_executor.prepare_execution(request.nodes, request.edges, request.breakpoints)
        
        # Start executing based on mode
        if debug_state.mode in ["running", "stepping"]:
            asyncio.create_task(debug_execution_loop())
        
        await broadcast_debug_update()
        await broadcast_status_update()
        
        return {"success": True, "message": "Debug session started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def debug_execution_loop():
    """Main debug execution loop"""
    global debug_executor, debug_state
    
    while debug_state.is_debugging and debug_state.mode in ["running", "stepping"]:
        try:
            should_continue = await debug_executor.execute_next_step()
            
            if not should_continue:
                break
                
            # If in stepping mode, pause after each step
            if debug_state.mode == "stepping":
                debug_state.mode = "paused"
                await broadcast_debug_update()
                break
                
            # If paused (e.g., at breakpoint), break the loop
            if debug_state.mode == "paused":
                break
                
            # Small delay between steps
            await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Error in debug execution: {e}")
            debug_state.mode = "error"
            await broadcast_debug_update()
            break

@app.post("/debug/control")
async def debug_control(request: Dict[str, Any]):
    """Control debugging (step, pause, resume, stop)"""
    try:
        global debug_state, current_status, debug_executor
        
        action = request.get("action")
        
        if action == "step":
            if debug_state.mode == "paused":
                debug_state.mode = "stepping"
                current_status.message = "Stepping to next node"
                # Execute one step
                asyncio.create_task(debug_execution_loop())
        elif action == "pause":
            debug_state.mode = "paused"
            current_status.message = "Execution paused"
        elif action == "resume":
            debug_state.mode = "running"
            current_status.message = "Execution resumed"
            # Resume execution
            asyncio.create_task(debug_execution_loop())
        elif action == "stop":
            debug_state.is_debugging = False
            debug_state.mode = "stopped"
            debug_state.current_node = None
            current_status.status = "idle"
            current_status.message = "Debug session stopped"
        
        await broadcast_debug_update()
        await broadcast_status_update()
        
        return {"success": True, "message": f"Debug action: {action}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug/state")
async def get_debug_state():
    """Get current debug state"""
    return debug_state.model_dump()

@app.post("/debug/breakpoints")
async def update_breakpoints(request: Dict[str, Any]):
    """Update breakpoints during debugging"""
    try:
        global debug_state
        
        debug_state.breakpoints = request.get("breakpoints", [])
        
        await broadcast_debug_update()
        
        return {"success": True, "message": "Breakpoints updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def broadcast_debug_update():
    """Broadcast debug state update to all connected clients"""
    await manager.broadcast({
        "type": "debug_update",
        "data": debug_state.model_dump()
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
