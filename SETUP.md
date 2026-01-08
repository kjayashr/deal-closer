# 🛠️ Setup Guide - DealCloser Sales AI Agent

A comprehensive, step-by-step guide to get DealCloser running locally on your machine.

---

## 📋 Table of Contents

- [Prerequisites](#-prerequisites)
- [Step 1: Clone and Install](#step-1-clone-and-install)
- [Step 2: Environment Setup](#step-2-environment-setup)
- [Step 3: Verify Installation](#step-3-verify-installation)
- [Step 4: Start the FastAPI Server](#step-4-start-the-fastapi-server)
- [Step 5: Test the API](#step-5-test-the-api)
- [Step 6: Run the Streamlit UI](#step-6-run-the-streamlit-ui)
- [Troubleshooting](#-troubleshooting)
- [Next Steps](#-next-steps)

---

## ✅ Prerequisites

Before you begin, make sure you have the following installed:

### Required

1. **Python 3.10 or higher**
   ```bash
   python --version
   # Should show: Python 3.10.x or higher
   ```
   - If you don't have Python, download from [python.org](https://www.python.org/downloads/)
   - On macOS, you can also use Homebrew: `brew install python@3.10`

2. **pip** (Python package manager)
   ```bash
   pip --version
   # Should show: pip 23.x.x or higher
   ```

3. **Anthropic API Key**
   - Sign up at [console.anthropic.com](https://console.anthropic.com)
   - Create an API key
   - Copy the key (starts with `sk-ant-...`)

### Optional (but recommended)

4. **OpenAI API Key** (for multi-provider racing and semantic caching)
   - Sign up at [platform.openai.com](https://platform.openai.com)
   - Create an API key
   - Copy the key (starts with `sk-...`)

5. **Git** (if cloning from repository)
   ```bash
   git --version
   ```

---

## Step 1: Clone and Install

### 1.1 Get the Code

If you have the repository URL:
```bash
git clone <repository-url>
cd DealCloser
```

Or if you already have the code:
```bash
cd /path/to/DealCloser
```

### 1.2 Create a Virtual Environment (Recommended)

Using a virtual environment keeps dependencies isolated:

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

You should see `(venv)` in your terminal prompt.

### 1.3 Install Dependencies

```bash
# Make sure you're in the DealCloser directory
pip install -r requirements.txt
```

This will install:
- FastAPI and Uvicorn (web server)
- Anthropic and OpenAI SDKs
- Streamlit (for the UI)
- Pytest (for testing)
- All other dependencies

**Expected output:**
```
Successfully installed fastapi-0.109.0 uvicorn-0.27.0 anthropic-0.18.0 ...
```

**If you get errors:**
- Make sure Python 3.10+ is installed
- Try upgrading pip: `pip install --upgrade pip`
- On macOS, you might need: `pip3 install -r requirements.txt`

---

## Step 2: Environment Setup

### 2.1 Create `.env` File

Create a `.env` file in the root directory (`DealCloser/`):

```bash
# In the DealCloser directory
touch .env
```

Or on Windows:
```cmd
type nul > .env
```

### 2.2 Add Your API Keys

Open `.env` in a text editor and add:

```bash
# Required: Anthropic API Key
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Optional: OpenAI API Key (enables multi-provider racing)
OPENAI_API_KEY=sk-your-key-here

# Optional: Logging level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
```

**Important:**
- Replace `sk-ant-your-key-here` with your actual Anthropic API key
- Replace `sk-your-key-here` with your actual OpenAI API key (if you have one)
- Never commit `.env` to git (it's already in `.gitignore`)

### 2.3 Verify `.env` File

```bash
# Check that the file exists and has content
cat .env
# Should show your API keys (be careful not to share these!)
```

---

## Step 3: Verify Installation

### 3.1 Check Python Packages

```bash
# Verify key packages are installed
python -c "import fastapi; print('FastAPI:', fastapi.__version__)"
python -c "import anthropic; print('Anthropic SDK installed')"
python -c "import streamlit; print('Streamlit installed')"
```

### 3.2 Check Configuration Files

```bash
# Verify config files exist
ls sales_agent/config/
# Should show:
# - principles.json
# - situations.json
# - principle_selector.json
# - capture_schema.json
# - settings.py
```

### 3.3 Test Import

```bash
# Test that the code can be imported
cd sales_agent
python -c "from config.settings import config; print('Config loaded:', config.ANTHROPIC_API_KEY[:10] + '...')"
cd ..
```

If you see an error about missing API key, check your `.env` file.

---

## Step 4: Start the FastAPI Server

### 4.1 Navigate to Sales Agent Directory

```bash
cd sales_agent
```

### 4.2 Start the Server

```bash
uvicorn api.main:app --reload
```

**What this does:**
- Starts the FastAPI server on `http://localhost:8000`
- `--reload` enables auto-reload on code changes (useful for development)

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using WatchFiles
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

### 4.3 Verify Server is Running

Open your browser and go to:
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Root**: http://localhost:8000/

You should see:
- **`/docs`**: Interactive API documentation (Swagger UI)
- **`/health`**: `{"status": "ok", "llm_connection": "ok", ...}`
- **`/`**: API information

**If you see errors:**
- Check that port 8000 is not already in use
- Verify your `.env` file has the correct API keys
- See [Troubleshooting](#-troubleshooting) below

### 4.4 Keep Server Running

**Keep this terminal window open!** The server needs to keep running.

**To stop the server:**
- Press `Ctrl+C` in the terminal

---

## Step 5: Test the API

### 5.1 Using cURL (Command Line)

Open a **new terminal window** (keep the server running in the first one).

```bash
# Test the /chat endpoint
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-001",
    "message": "This product is too expensive",
    "product_context": {"name": "ErgoChair", "price": 899}
  }'
```

**Expected response:**
```json
{
  "customer_facing": {
    "response": "I understand price is important..."
  },
  "agent_dashboard": {
    "detection": {
      "detected_situation": "price_shock_in_store",
      "situation_confidence": 0.92,
      ...
    },
    ...
  }
}
```

### 5.2 Using the Interactive API Docs

1. Go to http://localhost:8000/docs
2. Click on `POST /chat`
3. Click "Try it out"
4. Edit the request body:
   ```json
   {
     "session_id": "test-001",
     "message": "I need a mattress for my back pain",
     "product_context": {"name": "Aurora Mattress", "price": 45000}
   }
   ```
5. Click "Execute"
6. See the response below

### 5.3 Using Python Script

Create a test file `test_api.py`:

```python
import httpx
import json

response = httpx.post(
    "http://localhost:8000/chat",
    json={
        "session_id": "test-002",
        "message": "I've been having back pain for years",
        "product_context": {"name": "Aurora Mattress", "price": 45000}
    }
)

print(json.dumps(response.json(), indent=2))
```

Run it:
```bash
python test_api.py
```

### 5.4 Test Other Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Cache stats
curl http://localhost:8000/cache/stats

# Session info
curl http://localhost:8000/session/test-001
```

---

## Step 6: Run the Streamlit UI

### 6.1 Open a New Terminal

**Keep the FastAPI server running** in the first terminal. Open a **new terminal window**.

### 6.2 Navigate to Project Root

```bash
cd /path/to/DealCloser
```

Make sure you're in the root directory (where `streamlit_app.py` is located).

### 6.3 Activate Virtual Environment (if using one)

```bash
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows
```

### 6.4 Start Streamlit

```bash
streamlit run streamlit_app.py
```

**Expected output:**
```
You can now view your Streamlit app in your browser.

  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

### 6.5 Open the UI

The browser should open automatically. If not, go to:
**http://localhost:8501**

### 6.6 Use the UI

1. **Enter a customer message** in the sidebar:
   - Example: "The Aurora mattress looks good but ₹45,000 is a lot"

2. **Set options** (optional):
   - Session ID: `demo-001`
   - Channel: `website_chat`
   - Turn Number: `1`

3. **Click "Analyze"**

4. **View the results:**
   - Customer message display
   - Stage flow indicator
   - Situation detection
   - Context and qualification
   - **Grounding panel** (hero feature)
   - Recommended response
   - Fallback and next probe
   - Metrics

### 6.7 Configure API URL (if needed)

If your FastAPI server is running on a different URL:

```bash
# Set environment variable before starting Streamlit
export API_BASE_URL=http://localhost:8000
streamlit run streamlit_app.py
```

Or on Windows:
```cmd
set API_BASE_URL=http://localhost:8000
streamlit run streamlit_app.py
```

### 6.8 Stop Streamlit

Press `Ctrl+C` in the terminal.

---

## 🔧 Troubleshooting

### Problem: "Module not found" errors

**Solution:**
```bash
# Make sure you're in the virtual environment
source venv/bin/activate  # macOS/Linux

# Reinstall dependencies
pip install -r requirements.txt
```

### Problem: "ANTHROPIC_API_KEY not set"

**Solution:**
1. Check that `.env` file exists in the root directory
2. Verify the file has: `ANTHROPIC_API_KEY=sk-ant-...`
3. Make sure there are no spaces around the `=` sign
4. Restart the server after changing `.env`

### Problem: "Port 8000 already in use"

**Solution:**
```bash
# Find what's using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill the process, or use a different port:
uvicorn api.main:app --reload --port 8001
```

### Problem: "Cannot connect to API" in Streamlit

**Solution:**
1. Make sure FastAPI server is running (check http://localhost:8000/health)
2. Check the API URL in Streamlit (default is `http://localhost:8000`)
3. Set `API_BASE_URL` environment variable if using a different URL

### Problem: "Streamlit not found"

**Solution:**
```bash
# Install streamlit
pip install streamlit

# Or reinstall all dependencies
pip install -r requirements.txt
```

### Problem: API returns 500 errors

**Solution:**
1. Check server logs in the terminal where uvicorn is running
2. Verify API keys are correct in `.env`
3. Check that config files exist in `sales_agent/config/`
4. Try the health endpoint: `curl http://localhost:8000/health`

### Problem: Slow responses

**Solution:**
- This is normal for the first request (cold start)
- Subsequent requests should be faster (caching)
- Add `OPENAI_API_KEY` to enable multi-provider racing
- Check network connection

### Problem: Import errors when running from different directory

**Solution:**
- Always run uvicorn from `sales_agent/` directory:
  ```bash
  cd sales_agent
  uvicorn api.main:app --reload
  ```
- Always run streamlit from the root directory:
  ```bash
  cd /path/to/DealCloser
  streamlit run streamlit_app.py
  ```

---

## 🎯 Next Steps

### Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/unit/ --cov=sales_agent/engine --cov-report=html
```

### Explore the API

- Visit http://localhost:8000/docs for interactive API documentation
- Try different customer messages
- Check cache stats: http://localhost:8000/cache/stats
- Monitor LLM stats: http://localhost:8000/llm/stats

### Customize Configuration

- Edit `sales_agent/config/principles.json` to add/modify principles
- Edit `sales_agent/config/situations.json` to add/modify situations
- Adjust environment variables in `.env` for different behavior

### Read Documentation

- **[README.md](README.md)** - Overview and features
- **[OPTIMIZATION_GUIDE.md](OPTIMIZATION_GUIDE.md)** - Performance optimization
- **[API Reference](README.md#-api-reference)** - Complete API documentation

---

## 📞 Getting Help

If you're still stuck:

1. **Check the logs**: Look at the terminal output for error messages
2. **Verify setup**: Go through each step again carefully
3. **Check versions**: Make sure Python 3.10+ is installed
4. **Review error messages**: They usually point to the issue

---

## ✅ Quick Checklist

Before you start, make sure:

- [ ] Python 3.10+ installed
- [ ] Virtual environment created and activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] `.env` file created with `ANTHROPIC_API_KEY`
- [ ] Config files exist in `sales_agent/config/`
- [ ] FastAPI server starts without errors
- [ ] Health endpoint returns `{"status": "ok"}`
- [ ] Streamlit starts without errors
- [ ] UI loads at http://localhost:8501

---

**🎉 You're all set!** Start building amazing sales conversations with DealCloser.

