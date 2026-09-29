import os
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
os.environ["GOOGLE_CLOUD_PROJECT"] = "qwiklabs-gcp-01-dc80020db869"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"

import asyncio
import time
from app.agent import root_agent
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts import InMemoryArtifactService
from google.genai import types

async def run_demo():
    print("=" * 75)
    print("🎬 DEMO WALKTHROUGH: Smart Pantry Concierge Agent")
    print("=" * 75)

    session_service = InMemorySessionService()
    artifact_service = InMemoryArtifactService()

    runner = Runner(
        agent=root_agent,
        app_name="app",
        session_service=session_service,
        artifact_service=artifact_service,
        auto_create_session=True,
    )

    session_id = f"demo_session_{int(time.time())}"

    print("\n--- PROMPT 1: Pantry Inventory & Firestore Lookup ---")
    prompt1 = "What items are in my pantry right now?"
    print(f"User: {prompt1}\n")

    msg1 = types.Content(role="user", parts=[types.Part.from_text(text=prompt1)])

    async for event in runner.run_async(
        user_id="demo_user",
        session_id=session_id,
        new_message=msg1,
    ):
        if hasattr(event, "content") and event.content:
            for part in getattr(event.content, "parts", []):
                if hasattr(part, "text") and part.text:
                    print(f"Agent Response:\n{part.text}\n")
                if hasattr(part, "function_call") and part.function_call:
                    print(f"🛠️ Tool Call: {part.function_call.name}({part.function_call.args})")
                if hasattr(part, "function_response") and part.function_response:
                    print(f"✅ Tool Result: {part.function_response.name} -> {str(part.function_response.response)[:250]}...")

    print("\n" + "=" * 75)
    print("\n--- PROMPT 2: Recipe Matching & Image Generation ---")
    prompt2 = "Suggest a recipe using ingredients from my pantry and generate a visual serving idea image for it."
    print(f"User: {prompt2}\n")

    msg2 = types.Content(role="user", parts=[types.Part.from_text(text=prompt2)])

    async for event in runner.run_async(
        user_id="demo_user",
        session_id=session_id,
        new_message=msg2,
    ):
        if hasattr(event, "content") and event.content:
            for part in getattr(event.content, "parts", []):
                if hasattr(part, "text") and part.text:
                    print(f"Agent Response:\n{part.text}\n")
                if hasattr(part, "function_call") and part.function_call:
                    print(f"🛠️ Tool Call: {part.function_call.name}({part.function_call.args})")
                if hasattr(part, "function_response") and part.function_response:
                    print(f"✅ Tool Result: {part.function_response.name} -> {str(part.function_response.response)[:250]}...")

    print("\n" + "=" * 75)
    print("✨ DEMO COMPLETED SUCCESSFULLY!")
    print("=" * 75)

if __name__ == "__main__":
    asyncio.run(run_demo())
