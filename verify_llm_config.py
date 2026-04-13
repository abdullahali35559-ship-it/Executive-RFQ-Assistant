import os
from dotenv import load_dotenv
from models.pixtral_client import PixtralClient

load_dotenv()

def test_config():
    print("--- Verifying LLM Configuration ---")
    provider = os.getenv("LLM_PROVIDER")
    url = os.getenv("PIXTRAL_URL")
    api_key = os.getenv("PIXTRAL_API_KEY")
    
    print(f"Provider: {provider}")
    print(f"URL: {url}")
    print(f"API Key Found: {bool(api_key)}")
    
    if not api_key or api_key == "your_key_here":
        print("[!] Warning: API Key is still placeholder. Please update .env")
        return

    client = PixtralClient()
    try:
        print("\nTesting LLM Response (this might take a few seconds)...")
        response = client.chat("System", "Say 'LLM Config OK' if you can read this.")
        print(f"Response: {response}")
    except Exception as e:
        print(f"[X] LLM Error: {e}")

if __name__ == "__main__":
    test_config()
