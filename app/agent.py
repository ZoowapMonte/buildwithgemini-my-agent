# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os
import urllib.parse
import urllib.request
import uuid
from zoneinfo import ZoneInfo

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager
from google import genai
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools import ToolContext
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.cloud import firestore, storage
from google.genai import types

try:
    from .a2ui_utils import a2ui_callback
except (ImportError, ValueError):
    from a2ui_utils import a2ui_callback

# Hardcoded Project ID string & GCS Bucket string (REQUIRED for Agent Platform deployment)
FIRESTORE_PROJECT_ID = "qwiklabs-gcp-01-dc80020db869"
GCS_BUCKET_NAME = "smart-pantry-media-dc80020db869"
MEMORY_BANK_ID = "8170136104712798208"

db = firestore.Client(project=FIRESTORE_PROJECT_ID)

# Read agent engine runtime ID from deployment_metadata.json if available
agent_engine_resource_name = None
metadata_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "deployment_metadata.json")
if not os.path.exists(metadata_path):
    metadata_path = "deployment_metadata.json"

if os.path.exists(metadata_path):
    try:
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
            agent_engine_resource_name = metadata.get("remote_agent_runtime_id")
    except Exception:
        pass

code_executor = AgentEngineSandboxCodeExecutor(
    agent_engine_resource_name=agent_engine_resource_name
)


def memory_service_builder():
    """Builds VertexAiMemoryBankService pointing to the deployed Agent Engine Memory Bank."""
    return VertexAiMemoryBankService(
        project=FIRESTORE_PROJECT_ID,
        location="us-central1",
        agent_engine_id=MEMORY_BANK_ID,
    )


async def generate_memories_callback(callback_context: CallbackContext):
    """WRITE: after each turn, send the session events to Memory Bank for durable memory extraction."""
    try:
        await callback_context.add_session_to_memory()
    except Exception as e:
        print(f"Memory extraction notice: {e}")
    return None


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are the Smart Pantry Concierge assistant. You help users manage "
        "their pantry items, look up ingredients, add new stock, suggest "
        "recipes based on inventory, search live online recipes, geocode addresses, "
        "find nearby food places, generate food/dish images, execute Python code "
        "in a safe Agent Platform sandbox, and remember user facts/preferences across sessions.\n\n"
        "CRITICAL ALLERGY & MEMORY INSTRUCTION:\n"
        "Always record, remember, and strictly respect all user dietary restrictions and food allergies "
        "(such as peanut, tree nut, gluten, dairy, shellfish, soy, or egg allergies) across conversations. "
        "When the user mentions an allergy or dietary restriction, pay special attention to remember it. "
        "Before recommending or suggesting any recipe, meal, or pantry item, check all recalled user memories "
        "to ensure none of the ingredients conflict with the user's recorded allergies."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)


def list_pantry_items(category: str = "") -> list[dict]:
    """Lists items currently available in the user's pantry.

    Args:
        category: Optional category filter (e.g. 'Grains & Rice', 'Pantry Staples').

    Returns:
        A list of dictionaries representing pantry items.
    """
    collection_ref = db.collection("pantry_items")
    docs = collection_ref.stream()

    items = []
    for doc in docs:
        data = doc.to_dict()
        if category and category.lower() not in data.get("category", "").lower():
            continue
        items.append(data)
    return items


def add_pantry_item(
    name: str, category: str, quantity: float, unit: str, expiration_days: int = 30
) -> str:
    """Adds or updates an item in the user's pantry.

    Args:
        name: Name of the pantry item (e.g., 'Extra Virgin Olive Oil').
        category: Category of the item (e.g., 'Pantry Staples', 'Produce').
        quantity: Quantity count or weight (e.g., 2.0).
        unit: Measurement unit (e.g., 'bottles', 'kg', 'cans').
        expiration_days: Estimated shelf life in days.

    Returns:
        Confirmation string indicating successful insertion.
    """
    doc_id = name.lower().replace(" ", "_")
    item = {
        "name": name,
        "category": category,
        "quantity": quantity,
        "unit": unit,
        "expiration_days": expiration_days,
    }
    db.collection("pantry_items").document(doc_id).set(item)
    return f"Successfully added '{name}' ({quantity} {unit}) to pantry in category '{category}'."


def search_pantry_items(query: str) -> list[dict]:
    """Searches pantry items matching a search query.

    Args:
        query: Search keyword to match against item names or categories.

    Returns:
        Matching pantry item records.
    """
    collection_ref = db.collection("pantry_items")
    docs = collection_ref.stream()

    query_lower = query.lower()
    results = []
    for doc in docs:
        data = doc.to_dict()
        if query_lower in data.get("name", "").lower() or query_lower in data.get("category", "").lower():
            results.append(data)
    return results


def suggest_recipes(prep_time_minutes: int = 30) -> list[dict]:
    """Suggests recipes based on available ingredients in the pantry and maximum prep time.

    Args:
        prep_time_minutes: Maximum preparation time in minutes (default: 30).

    Returns:
        List of suggested recipes with name, prep time, required ingredients, and description.
    """
    items = list_pantry_items()
    recipes = [
        {
            "name": "Black Bean & Jasmine Rice Bowl",
            "prep_time_minutes": 15,
            "ingredients": ["Jasmine Rice", "Canned Black Beans", "Garlic Cloves", "Organic Olive Oil"],
            "description": "A quick and savory rice bowl topped with garlic black beans.",
        },
        {
            "name": "Garlic Aglio e Olio Pasta",
            "prep_time_minutes": 20,
            "ingredients": ["Whole Wheat Pasta", "Garlic Cloves", "Organic Olive Oil"],
            "description": "Simple and classic Italian pasta made with pantry staples.",
        },
        {
            "name": "Hearty Tomato & Black Bean Soup",
            "prep_time_minutes": 25,
            "ingredients": ["Tomato Soup", "Canned Black Beans", "Garlic Cloves"],
            "description": "A comforting soup combining tomato broth and black beans.",
        },
    ]

    matched = [r for r in recipes if r["prep_time_minutes"] <= prep_time_minutes]
    return matched


def fetch_online_recipe(query: str) -> list[dict]:
    """Fetches real recipes and cooking instructions from TheMealDB public food API.

    Args:
        query: Name of dish or main ingredient to search for (e.g. 'pasta', 'chicken', 'rice').

    Returns:
        List of recipe details including title, category, area, instructions, and thumbnail URL.
    """
    api_key = os.getenv("MEALDB_API_KEY", "1")
    encoded_query = urllib.parse.quote(query)
    url = f"https://www.themealdb.com/api/json/v1/{api_key}/search.php?s={encoded_query}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SmartPantryAgent/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            meals = data.get("meals")
            if not meals:
                return []

            results = []
            for meal in meals[:3]:
                results.append({
                    "id": meal.get("idMeal"),
                    "name": meal.get("strMeal"),
                    "category": meal.get("strCategory"),
                    "area": meal.get("strArea"),
                    "instructions": meal.get("strInstructions", "")[:250] + "...",
                    "thumbnail": meal.get("strMealThumb"),
                })
            return results
    except Exception as e:
        return [{"error": f"Failed to fetch recipe: {str(e)}"}]


def geocode_address(address: str) -> dict:
    """Converts a street address or location name into geographic coordinates (lat, lng).

    Args:
        address: The address or location string to geocode (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA').

    Returns:
        Dictionary containing formatted_address and location (lat, lng).
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not api_key or api_key == "PASTE_KEY_HERE":
        return {"error": "GOOGLE_MAPS_API_KEY is not configured in .env."}

    encoded_address = urllib.parse.quote(address)
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={api_key}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data.get("status") == "OK" and data.get("results"):
                result = data["results"][0]
                return {
                    "formatted_address": result.get("formatted_address"),
                    "location": result.get("geometry", {}).get("location"),
                }
            return {"error": f"Geocoding failed with status: {data.get('status')}"}
    except Exception as e:
        return {"error": f"Geocoding request failed: {str(e)}"}


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "grocery_store",
    radius_meters: float = 1000.0,
) -> list[dict]:
    """Finds nearby places of a given type around a geographic coordinate using Places API (New).

    Args:
        latitude: Center latitude coordinate.
        longitude: Center longitude coordinate.
        place_type: Type of place to search for (e.g., 'grocery_store', 'supermarket', 'restaurant').
        radius_meters: Search radius in meters (default: 1000.0).

    Returns:
        List of matching places with name, address, and location coordinates.
    """
    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "")
    if not api_key or api_key == "PASTE_KEY_HERE":
        return [{"error": "GOOGLE_MAPS_API_KEY is not configured in .env."}]

    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
    }
    payload = {
        "includedTypes": [place_type],
        "maxResultCount": 10,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": latitude, "longitude": longitude},
                "radius": radius_meters,
            }
        },
    }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            places = data.get("places", [])
            results = []
            for place in places:
                results.append({
                    "name": place.get("displayName", {}).get("text"),
                    "address": place.get("formattedAddress"),
                    "location": place.get("location"),
                })
            return results
    except Exception as e:
        return [{"error": f"Places API request failed: {str(e)}"}]


async def generate_pantry_item_image(item_name: str, tool_context: ToolContext) -> str:
    """Generates a visual image for a pantry item or dish using gemini-3.1-flash-lite-image in the global region.

    Saves the image bytes as an artifact in Playground and uploads directly to public Cloud Storage.

    Args:
        item_name: Name or description of the pantry item or food dish to generate an image for.
        tool_context: ADK ToolContext injected at runtime to save artifacts.

    Returns:
        The public HTTPS URL of the uploaded image in Cloud Storage.
    """
    client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT_ID, location="global")
    prompt = f"Professional food photography of {item_name}, clean kitchen lighting, delicious presentation"

    response = client.models.generate_content(
        model="gemini-3.1-flash-lite-image",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
        ),
    )

    image_bytes = None
    mime_type = "image/jpeg"
    for part in response.parts:
        if part.inline_data:
            image_bytes = part.inline_data.data
            if part.inline_data.mime_type:
                mime_type = part.inline_data.mime_type
            break

    if not image_bytes:
        return "Error: Failed to generate image bytes."

    ext = "png" if "png" in mime_type else "jpg"
    filename = f"{item_name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}.{ext}"

    try:
        artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
        await tool_context.save_artifact(filename, artifact_part)
    except Exception as err:
        pass

    storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
    bucket = storage_client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(filename)
    blob.upload_from_string(image_bytes, content_type=mime_type)

    public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"
    return public_url


async def generate_pantry_item_video(item_name: str, tool_context: ToolContext) -> str:
    """Generates a short video for a pantry item or dish using gemini-omni-flash-preview in the global region.

    Saves the video bytes as an artifact in Playground and uploads directly to public Cloud Storage.

    Args:
        item_name: Name or description of the pantry item or food dish to generate a video for.
        tool_context: ADK ToolContext injected at runtime to save artifacts.

    Returns:
        The public HTTPS URL of the uploaded video in Cloud Storage.
    """
    client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT_ID, location="global")
    prompt = f"A short video of {item_name}, clean kitchen lighting, delicious presentation"

    try:
        operation = client.models.generate_videos(
            model="gemini-omni-flash-preview",
            prompt=prompt,
        )
        while not operation.done:
            time.sleep(5)
            operation = client.operations.get(operation)

        video_bytes = None
        mime_type = "video/mp4"

        if operation.result and operation.result.generated_videos:
            v = operation.result.generated_videos[0].video
            if hasattr(v, "video_bytes") and v.video_bytes:
                video_bytes = v.video_bytes
            elif hasattr(v, "uri") and v.uri:
                uri = v.uri
                if uri.startswith("gs://"):
                    gs_path = uri[5:]
                    b_name, b_path = gs_path.split("/", 1)
                    storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
                    video_bytes = storage_client.bucket(b_name).blob(b_path).download_as_bytes()
                elif uri.startswith("http://") or uri.startswith("https://"):
                    req = urllib.request.urlopen(uri)
                    video_bytes = req.read()

        if not video_bytes:
            return "Error: Failed to generate video bytes."

        filename = f"{item_name.lower().replace(' ', '_')}_{uuid.uuid4().hex[:6]}.mp4"

        try:
            artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
            await tool_context.save_artifact(filename, artifact_part)
        except Exception as err:
            pass

        storage_client = storage.Client(project=FIRESTORE_PROJECT_ID)
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{GCS_BUCKET_NAME}/{filename}"
        return public_url
    except Exception as e:
        return f"Error generating video: {str(e)}"


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-2.5-flash",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    code_executor=code_executor,
    tools=[
        PreloadMemoryTool(),
        list_pantry_items,
        add_pantry_item,
        search_pantry_items,
        suggest_recipes,
        fetch_online_recipe,
        geocode_address,
        find_nearby_places,
        generate_pantry_item_image,
        generate_pantry_item_video,
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
