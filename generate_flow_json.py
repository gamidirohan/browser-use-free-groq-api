import json
from pathlib import Path

# Path to your agent history file (update if needed)
HISTORY_PATH = Path('agent_history.json')
FLOW_PATH = Path('agent-flow-visualizer/public/flow.json')

if not HISTORY_PATH.exists():
    raise FileNotFoundError(f"{HISTORY_PATH} not found. Run your agent and export history first.")

with open(HISTORY_PATH, encoding='utf-8') as f:
    data = json.load(f)

nodes = []
edges = []
y = 20
node_ids = []
for i, h in enumerate(data["history"]):
    if not h["model_output"]:
        continue
    for j, action in enumerate(h["model_output"]["action"]):
        node_id = f"{i}-{j}"
        label = list(action.keys())[0]
        color_map = {
            'go_to_url': '#b2f7b8',
            'input_text': '#b3d8fd',
            'click_element': '#ffd59e',
            'extract_content': '#d6b3fd',
            'done': '#ffb3b3',
        }
        color = color_map.get(label, '#eee')
        nodes.append({
            "id": node_id,
            "position": {"x": 100, "y": y},
            "data": {"label": label.replace('_', ' ').title()},
            "style": {"background": color}
        })
        node_ids.append(node_id)
        if len(node_ids) > 1:
            edges.append({"id": f"e{node_ids[-2]}-{node_id}", "source": node_ids[-2], "target": node_id})
        y += 100

with open(FLOW_PATH, "w", encoding='utf-8') as f:
    json.dump({"nodes": nodes, "edges": edges}, f, indent=2)

print(f"Wrote {FLOW_PATH} with {len(nodes)} nodes and {len(edges)} edges.")
