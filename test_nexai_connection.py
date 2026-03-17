import os
import requests
import json
from dotenv import load_dotenv

def test_nexai_connection():
    # Load environment variables from .env
    load_dotenv()
    
    api_key = os.getenv("REMOTE_API_KEY")
    base_url = os.getenv("REMOTE_BASE_URL", "https://nexai.newdev.net/api/v1")
    model = os.getenv("REMOTE_MODEL", "gpt-4o-mini")

    print(f"--- Testing NEXAI Connection ---")
    print(f"Base URL: {base_url}")
    print(f"Model: {model}")
    print(f"API Key: {api_key[:5]}...{api_key[-5:] if api_key else 'None'}")
    
    if not api_key:
        print("❌ Error: REMOTE_API_KEY not found in .env")
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Say hello from NEXAI connection test script"}],
        "stream": False
    }

    try:
        print(f"📡 Sending request to {base_url}/chat/completions...")
        response = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=15
        )
        
        if response:
            print(f"Status Code: {response.status_code}")
            
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print(f"✅ Success! Response from NEXAI:")
            print(f"--------------------------------")
            print(content)
            print(f"--------------------------------")
        else:
            print(f"❌ Failed! Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error during connection test: {e}")

if __name__ == "__main__":
    test_nexai_connection()
