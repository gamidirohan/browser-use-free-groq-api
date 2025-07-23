# Browser-Use Free GROQ API

A powerful web automation framework that combines browser-use agents with JavaScript/Python script generation and a React flow visualizer. This application allows you to automate browser tasks, generate replay scripts in multiple languages, and visualize agent workflows with a 15-second captcha wait feature.

## 🚀 Features

- **Dual Script Generation**: Generate both Python and JavaScript Playwright scripts from agent history
- **Captcha Wait Integration**: Built-in 15-second delay for manual captcha solving
- **React Flow Visualizer**: Interactive web interface to visualize agent workflows
- **FastAPI Backend**: RESTful API for running agents and managing workflows
- **Multi-Language Support**: Support for various LLM providers (OpenAI, Groq, Anthropic, etc.)
- **Browser Context Management**: Advanced browser session handling with cookie persistence

## 📋 Prerequisites

- **Python 3.8+**
- **Node.js 16+** (for React flow visualizer)
- **Chrome/Chromium browser**
- **API Keys** for your chosen LLM provider

## 🛠️ Installation & Setup

### 1. Clone Repository
```powershell
git clone <repository-url>
cd browser-use-free-groq-api
```

### 2. Python Environment Setup
```powershell
# Create virtual environment
python -m venv myenv

# Activate virtual environment
myenv\Scripts\activate

# Install Python dependencies
pip install -r requirements-backend.txt
```

### 3. React Flow Visualizer Setup
```powershell
# Navigate to React app
cd agent-flow-visualizer

# Install Node.js dependencies
npm install

# Return to root directory
cd ..
```

### 4. Environment Variables
Create a `.env` file in the root directory:
```env
# LLM Provider (choose one)
OPENAI_API_KEY=your_openai_key_here
GROQ_API_KEY=your_groq_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here

# Optional: Browser settings
CHROME_INSTANCE_PATH=/path/to/chrome
CHROME_REMOTE_DEBUGGING_PORT=9222
```

## 🏃‍♂️ Running the Application

### Backend Server
Start the FastAPI backend in one terminal:
```powershell
python backend.py
```
- Backend runs on: `http://localhost:8000`
- API docs available at: `http://localhost:8000/docs`

### React Flow Visualizer
Start the React frontend in another terminal:
```powershell
cd agent-flow-visualizer
npm start
```
- Frontend runs on: `http://localhost:3000`
- Automatically connects to the backend API

## 🤖 Usage Examples

### 1. Using the Web Interface
1. Open `http://localhost:3000`
2. Enter your task description
3. Select model and script language (Python/JavaScript)
4. Click "Run Agent"
5. Wait for the 15-second captcha delay
6. Monitor progress and view generated scripts

### 2. Using the API Directly
```python
import requests

# Run an agent task
response = requests.post("http://localhost:8000/run-agent", json={
    "task": "Search for Python tutorials on Google",
    "model": "gpt-4o",
    "script_language": "javascript"
})

# Get agent status
status = requests.get("http://localhost:8000/status")

# Download generated script
script = requests.get("http://localhost:8000/download-script")
```

### 3. Command Line Usage
```python
from browser_use import Agent
from langchain_openai import ChatOpenAI

# Create agent with captcha wait
agent = Agent(
    task="Navigate to example.com and take a screenshot",
    llm=ChatOpenAI(model="gpt-4o"),
    playwright_script_language="javascript"  # or "python"
)

# Run agent (includes 15-second captcha wait)
history = await agent.run()

# Generate replay script
script_path = history.save_as_playwright_script(
    path="./generated_script.js",
    language="javascript"
)
```

## 🔧 Key Features Explained

### 15-Second Captcha Wait
- **Purpose**: Allows manual captcha solving before automation begins
- **Trigger**: Activates when browser context is initialized
- **Location**: Built into browser session initialization and generated scripts
- **Customizable**: Can be modified in `browser_use/browser/context.py`

### Script Generation
- **Python Scripts**: Full Playwright automation with helper functions
- **JavaScript Scripts**: Node.js compatible with same functionality
- **Features**: XPath fallback, sensitive data replacement, error handling
- **Output**: Self-contained executable scripts

### React Flow Visualizer
- **Purpose**: Visual representation of agent workflows
- **Features**: Real-time updates, task monitoring, script download
- **Technology**: React Flow with FastAPI backend integration

## 📁 Project Structure

```
browser-use-free-groq-api/
├── backend.py                     # FastAPI server
├── browser_use/                   # Core browser automation
│   ├── agent/                     # Agent logic and script generation
│   │   ├── playwright_script_generator.py      # Python script generation
│   │   ├── playwright_script_generator_js.py   # JavaScript script generation
│   │   ├── playwright_script_helpers.py        # Python helpers
│   │   └── playwright_script_helpers.js        # JavaScript helpers
│   ├── browser/                   # Browser management
│   └── controller/                # Action registry
├── agent-flow-visualizer/         # React frontend
│   ├── src/                       # React components
│   └── public/                    # Static assets
├── examples/                      # Usage examples
├── tests/                         # Test suite
└── docs/                          # Documentation
```

## 🧪 Testing

### Backend Tests
```powershell
# Test script generation
python test_script_generation_wait.py

# Test backend functionality
python test_backend_js.py

# Test captcha wait
python test_captcha_wait.py
```

### Running Full Test Suite
```powershell
pytest tests/
```

## 📝 Development & Contributing

### Making Changes

1. **Create Feature Branch**
```powershell
git checkout -b feature/your-feature-name
```

2. **Make Your Changes**
- Follow existing code patterns
- Add tests for new functionality
- Update documentation as needed

3. **Test Your Changes**
```powershell
# Run tests
pytest tests/

# Test backend
python backend.py

# Test frontend
cd agent-flow-visualizer && npm start
```

4. **Commit Guidelines**
```powershell
# Conventional commit format
git add .
git commit -m "feat: add new script generation feature"
git commit -m "fix: resolve captcha wait timing issue"
git commit -m "docs: update README with new features"
```

### Commit Types
- `feat:` New features
- `fix:` Bug fixes
- `docs:` Documentation changes
- `style:` Code style changes
- `refactor:` Code refactoring
- `test:` Test additions/changes
- `chore:` Maintenance tasks

### Pull Request Process

1. **Push Changes**
```powershell
git push origin feature/your-feature-name
```

2. **Create Pull Request**
- Use descriptive title and description
- Link related issues
- Add screenshots for UI changes
- Ensure all tests pass

3. **Code Review**
- Address reviewer feedback
- Make requested changes
- Keep commits clean and focused

## 🔍 API Endpoints

### Core Endpoints
- `POST /run-agent` - Execute agent task
- `GET /status` - Get current agent status
- `GET /download-script` - Download generated script
- `GET /history` - Get agent execution history
- `POST /run-replay` - Execute replay script
- `GET /script-info` - Get script information

### Example Requests
```bash
# Run agent with JavaScript output
curl -X POST "http://localhost:8000/run-agent" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Search for Python on Google",
    "model": "gpt-4o",
    "script_language": "javascript"
  }'

# Check status
curl "http://localhost:8000/status"

# Download script
curl "http://localhost:8000/download-script" -o script.js
```

## 🐛 Troubleshooting

### Common Issues

1. **Browser Launch Fails**
```
Error: Browser launch failed
Solution: Ensure Chrome is installed and accessible
```

2. **API Key Issues**
```
Error: Invalid API key
Solution: Check .env file and API key validity
```

3. **Port Conflicts**
```
Error: Port already in use
Solution: Stop other services or change ports in config
```

4. **Captcha Wait Not Working**
```
Issue: No 15-second delay
Solution: Check browser context initialization in logs
```

### Debug Mode
Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📊 Performance & Limitations

### Performance
- **Script Generation**: ~1-2 seconds per script
- **Agent Execution**: Varies by task complexity
- **Memory Usage**: ~100-500MB depending on browser content

### Limitations
- **Captcha Wait**: Fixed at 15 seconds (customizable in code)
- **Browser Support**: Chrome/Chromium recommended
- **Concurrent Agents**: Single agent execution at a time

## 🔐 Security Considerations

- **Sensitive Data**: Automatically replaced in generated scripts
- **API Keys**: Store in `.env` file, never commit
- **Browser Security**: Disable security only when necessary
- **CORS**: Configured for localhost development

## 📈 Roadmap

- [ ] Multiple concurrent agent support
- [ ] Custom captcha wait duration
- [ ] Additional script languages (C#, Java)
- [ ] Advanced flow visualization
- [ ] Cloud deployment support
- [ ] Database integration for history

## 🤝 Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Browser-use framework for core automation
- Playwright for browser automation
- React Flow for visualization
- FastAPI for backend framework

## 📞 Support

- **Issues**: Create GitHub issues for bugs
- **Discussions**: Use GitHub discussions for questions
- **Documentation**: Check `/docs` folder for detailed guides

---

**Happy Automating! 🤖✨**