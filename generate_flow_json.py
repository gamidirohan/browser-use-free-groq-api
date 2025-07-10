import json
from pathlib import Path

# Path to your agent history file (update if needed)
HISTORY_PATH = Path('agent_history.json')
FLOW_PATH = Path('agent-flow-visualizer/public/flow.json')

def create_sample_data():
    """Create sample flow data for testing"""
    return {
        "history": [
            {
                "model_output": {
                    "current_state": {
                        "next_goal": "Navigate to GitHub"
                    },
                    "action": [
                        {"go_to_url": {"url": "https://github.com"}}
                    ]
                }
            },
            {
                "model_output": {
                    "current_state": {
                        "next_goal": "Search for browser-use repository"
                    },
                    "action": [
                        {"input_text": {"index": 5, "text": "browser-use"}}
                    ]
                }
            },
            {
                "model_output": {
                    "current_state": {
                        "next_goal": "Submit the search"
                    },
                    "action": [
                        {"click_element": {"index": 3, "interacted_element": {"xpath": "//button[@type='submit'][1]"}}}
                    ]
                }
            },
            {
                "model_output": {
                    "current_state": {
                        "next_goal": "Extract contributors information"
                    },
                    "action": [
                        {"extract_page_content": {"goal": "Get list of contributors with their contributions"}}
                    ]
                }
            },
            {
                "model_output": {
                    "current_state": {
                        "next_goal": "Complete the task"
                    },
                    "action": [
                        {"done": {"text": "Successfully extracted contributors list", "success": True}}
                    ]
                }
            }
        ]
    }

if not HISTORY_PATH.exists():
    print(f"{HISTORY_PATH} not found. Using sample data for demonstration.")
    data = create_sample_data()
else:
    with open(HISTORY_PATH, encoding='utf-8') as f:
        data = json.load(f)

def create_detailed_label(action_name, action_params, step_index, action_index):
    """Create a detailed label for the node based on action type and parameters"""
    
    if action_name == 'go_to_url':
        url = action_params.get('url', '')
        # Truncate long URLs
        display_url = url if len(url) < 40 else url[:37] + '...'
        return f"Go to URL\n{display_url}"
    
    elif action_name == 'click_element':
        index = action_params.get('index', 'N/A')
        # Get element info if available
        element_info = action_params.get('interacted_element', {})
        xpath = element_info.get('xpath', '') if element_info else ''
        if xpath:
            # Extract tag name from xpath for display
            tag_match = xpath.split('/')[-1] if '/' in xpath else xpath
            return f"Click Element\nIndex: {index}\nTag: {tag_match}"
        return f"Click Element\nIndex: {index}"
    
    elif action_name == 'input_text':
        index = action_params.get('index', 'N/A')
        text = action_params.get('text', '')
        # Truncate long text
        display_text = text if len(text) < 20 else text[:17] + '...'
        return f"Input Text\nIndex: {index}\nText: \"{display_text}\""
    
    elif action_name == 'extract_content' or action_name == 'extract_page_content':
        goal = action_params.get('goal', action_params.get('value', ''))
        display_goal = goal if len(goal) < 25 else goal[:22] + '...'
        return f"Extract Content\nGoal: {display_goal}"
    
    elif action_name == 'scroll_down':
        amount = action_params.get('amount', 'default')
        return f"Scroll Down\nAmount: {amount}"
    
    elif action_name == 'scroll_up':
        amount = action_params.get('amount', 'default')
        return f"Scroll Up\nAmount: {amount}"
    
    elif action_name == 'search_google':
        query = action_params.get('query', '')
        display_query = query if len(query) < 25 else query[:22] + '...'
        return f"Search Google\nQuery: \"{display_query}\""
    
    elif action_name == 'open_tab':
        url = action_params.get('url', '')
        display_url = url if len(url) < 30 else url[:27] + '...'
        return f"Open New Tab\n{display_url}"
    
    elif action_name == 'close_tab':
        return "Close Tab"
    
    elif action_name == 'switch_tab':
        page_id = action_params.get('page_id', 'N/A')
        return f"Switch Tab\nPage ID: {page_id}"
    
    elif action_name == 'send_keys':
        keys = action_params.get('keys', '')
        return f"Send Keys\nKeys: {keys}"
    
    elif action_name == 'wait':
        seconds = action_params.get('seconds', 1)
        return f"Wait\n{seconds} seconds"
    
    elif action_name == 'done':
        text = action_params.get('text', '')
        success = action_params.get('success', False)
        status = "✓ Success" if success else "✗ Failed"
        if text:
            display_text = text if len(text) < 30 else text[:27] + '...'
            return f"Done - {status}\n{display_text}"
        return f"Done - {status}"
    
    else:
        # Fallback for unknown actions
        return f"{action_name.replace('_', ' ').title()}\nStep {step_index + 1}.{action_index + 1}"

nodes = []
edges = []
y = 50  # Start with more space from top
x = 150  # Center nodes better
node_ids = []
step_counter = 0

for i, h in enumerate(data["history"]):
    if not h["model_output"]:
        continue
    
    # Get the step's goal/context if available
    step_goal = ""
    if h["model_output"].get("current_state"):
        step_goal = h["model_output"]["current_state"].get("next_goal", "")
    
    step_actions = h["model_output"]["action"]
    
    # If this step has multiple actions, arrange them horizontally
    if len(step_actions) > 1:
        start_x = x - (len(step_actions) - 1) * 150 // 2
        current_x = start_x
    else:
        current_x = x
    
    for j, action in enumerate(step_actions):
        node_id = f"{i}-{j}"
        action_name = list(action.keys())[0]
        action_params = action[action_name] if action[action_name] else {}
        
        # Create detailed label
        detailed_label = create_detailed_label(action_name, action_params, i, j)
        
        # Color mapping with more colors for different actions
        color_map = {
            'go_to_url': '#b2f7b8',           # Light green
            'input_text': '#b3d8fd',          # Light blue
            'click_element': '#ffd59e',       # Light orange
            'extract_content': '#d6b3fd',     # Light purple
            'extract_page_content': '#d6b3fd', # Light purple
            'done': '#ffb3b3',                # Light red
            'scroll_down': '#ffe5b3',         # Light yellow
            'scroll_up': '#ffe5b3',           # Light yellow
            'search_google': '#c2f0c2',       # Mint green
            'open_tab': '#b3e6ff',            # Light cyan
            'close_tab': '#ffcccc',           # Light pink
            'switch_tab': '#e6ccff',          # Lavender
            'send_keys': '#f0e6ff',           # Very light purple
            'wait': '#f5f5dc',                # Beige
        }
        
        color = color_map.get(action_name, '#eee')
        
        # Add step context to tooltip or as subtitle
        subtitle = f"Step {i + 1}.{j + 1}"
        if step_goal:
            subtitle += f" | Goal: {step_goal[:30]}{'...' if len(step_goal) > 30 else ''}"
        
        nodes.append({
            "id": node_id,
            "position": {"x": current_x, "y": y},
            "data": {
                "label": detailed_label,
                "subtitle": subtitle
            },
            "style": {"background": color}
        })
        node_ids.append(node_id)
        
        # Connect to previous node(s)
        if len(node_ids) > 1:
            edges.append({"id": f"e{node_ids[-2]}-{node_id}", "source": node_ids[-2], "target": node_id})
        
        # Move x position for next action in the same step
        if len(step_actions) > 1:
            current_x += 300
    
    # Move to next row for next step, add more space between steps
    y += 150

with open(FLOW_PATH, "w", encoding='utf-8') as f:
    json.dump({"nodes": nodes, "edges": edges}, f, indent=2)

print(f"Wrote {FLOW_PATH} with {len(nodes)} nodes and {len(edges)} edges.")
