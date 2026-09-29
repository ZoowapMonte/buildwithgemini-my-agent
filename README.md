# 🌿 Smart Pantry Concierge

**Smart Pantry Concierge** is an AI-powered conversational assistant built using Google's **Agent Development Kit (ADK)** and deployed on **Agent Platform**. It helps users manage their pantry inventory, search recipes, query nearby grocery stores, remember dietary restrictions, and generate visual serving ideas and video demonstrations.

---

## ✨ Features & Capabilities

Based on the agent implementation in `app/`, the following capabilities and Google Cloud services are fully wired:

### 📦 1. Pantry Inventory Management (Firestore Database)
- **`list_pantry_items`**: Retrieves all items stored in Google Cloud Firestore.
- **`add_pantry_item`**: Adds new pantry items with category, quantity, unit, and expiration timeframe.
- **`search_pantry_items`**: Searches for specific ingredients in the inventory by name or category.

### 🧠 2. Cross-Session Long-Term Memory (Vertex AI Memory Bank)
- **`PreloadMemoryTool` & Callbacks**: Automatically remembers and recalls user dietary preferences, household details, and allergies across chat sessions using Vertex AI Memory Bank.

### 🍲 3. Smart Recipe Matching & External Search
- **`suggest_recipes`**: Matches available pantry items with savory recipes.
- **`fetch_online_recipe`**: Queries external culinary APIs (TheMealDB) to fetch detailed online recipes and instructions.

### 🖼️ 4. Multimodal Generation & Public Media Storage (GCS & Vertex AI)
- **`generate_pantry_item_image`**: Generates high-quality food dish photography using `gemini-3.1-flash-lite-image` in the `global` region, saves artifacts to ADK, and uploads image bytes to Google Cloud Storage (`gs://smart-pantry-media-...`).
- **`generate_pantry_item_video`**: Generates short culinary videos using `gemini-omni-flash-preview` in the `global` region, saves artifacts, and stores video bytes in Cloud Storage.

### 📍 5. Location Services (Google Maps & Places API)
- **`geocode_address`**: Converts street addresses into geographic coordinates.
- **`find_nearby_places`**: Locates nearby grocery stores and food markets using the Places API (New).

### 🖥️ 6. Rich UI Rendering (A2UI v0.8) & Secure Execution
- **A2UI v0.8 Integration**: Renders rich interactive cards, lists, columns, and icons in the frontend via `a2ui_callback`.
- **Sandbox Code Executor**: Safely executes Python code blocks using `AgentEngineSandboxCodeExecutor`.

---

## 🛠️ Architecture & Tech Stack

- **Framework**: Python, Google Agent Development Kit (ADK), FastAPI
- **LLM Engine**: Gemini (`gemini-2.5-flash`)
- **Cloud Services**:
  - Vertex AI Reasoning Engine / Agent Runtime
  - Vertex AI Memory Bank
  - Google Cloud Firestore (Datastore)
  - Google Cloud Storage (Media Bucket)
  - Google Cloud Run (Frontend Chat UI)
  - Google Maps & Places API

---

## 🚀 Local Development & Setup

### Prerequisites
- Python 3.10+
- `uv` package manager (`pip install uv`)
- Google Cloud CLI (`gcloud`) authenticated to your GCP project

### 1. Install Dependencies
```bash
uv sync
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory:
```bash
GOOGLE_GENAI_USE_VERTEXAI=True
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-east1
GOOGLE_MAPS_API_KEY=your-google-maps-api-key
```

### 3. Launch Local ADK Playground
To start the local ADK Web server with Memory Bank integration:
```bash
uv run adk web . --port 8080 --reload_agents --memory_service_uri=agentengine://<YOUR_AGENT_ENGINE_ID>
```

### 4. Run the Custom Chat Frontend
To run the FastAPI proxy and chat interface locally:
```bash
cd frontend
export AGENT_ENGINE_RESOURCE_NAME="projects/<PROJECT_NUMBER>/locations/us-east1/reasoningEngines/<REASONING_ENGINE_ID>"
export AGENT_DIRECTORY="app"
uvicorn main:app --host 0.0.0.0 --port 8000
```
Then open `http://localhost:8000` in your web browser.

---

## 🚢 Deployment Instructions

### Deploy Agent to Agent Platform
```bash
agents-cli deploy --no-confirm-project --update-env-vars GOOGLE_MAPS_API_KEY=YOUR_API_KEY
```

### Deploy Frontend to Cloud Run
```bash
gcloud run deploy my-agent-frontend \
  --source ./frontend \
  --region us-central1 \
  --set-env-vars AGENT_ENGINE_RESOURCE_NAME="<REASONING_ENGINE_ID>",AGENT_DIRECTORY="app"
```
