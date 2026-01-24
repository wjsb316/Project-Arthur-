import asyncio
import os
import httpx
import sys

async def check_api():
    api_key = os.getenv("XAI_API_KEY")
    if not api_key:
        print("Error: XAI_API_KEY environment variable not set.")
        print("Please set it with: export XAI_API_KEY='your-key-here'")
        return

    base_url = "https://api.x.ai/v1"
    headers = {"Authorization": f"Bearer {api_key}"}

    print(f"Checking API key against {base_url}...")

    async with httpx.AsyncClient() as client:
        # 1. Check User/API Key info (if there's an endpoint, otherwise standard models check)
        # Using /api-key if it exists, otherwise relying on /models
        try:
            response = await client.get(f"{base_url}/api-key", headers=headers)
            if response.status_code == 200:
                print("API Key info:", response.json())
            else:
                print(f"API Key check endpoint returned {response.status_code} (This might be expected if endpoint doesn't exist)")
        except Exception as e:
            print(f"API Key check failed: {e}")

        # 2. List Models
        print("\nListing available models...")
        try:
            # Try /models first (standard OpenAI)
            response = await client.get(f"{base_url}/models", headers=headers)
            if response.status_code == 200:
                models = response.json().get("data", [])
                print(f"Found {len(models)} models:")
                for model in models:
                    print(f" - {model['id']}")
            else:
                print(f"Failed to list models via /models: {response.status_code} {response.text}")
                
                # Fallback to /language-models if /models fails
                print("Trying /language-models...")
                response = await client.get(f"{base_url}/language-models", headers=headers)
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    print(f"Found {len(models)} models:")
                    for model in models:
                         print(f" - {model['id']}")
                else:
                    print(f"Failed to list models via /language-models: {response.status_code} {response.text}")

        except Exception as e:
            print(f"Model list failed: {e}")

if __name__ == "__main__":
    asyncio.run(check_api())
