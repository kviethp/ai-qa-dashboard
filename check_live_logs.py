import requests
import json
import sys
from dotenv import load_dotenv

load_dotenv()

# Fix charmap error on Windows
if sys.platform == "win32":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

def check_logs():
    url = "https://ai-qa-agents-default-rtdb.firebaseio.com/live_logs.json"
    response = requests.get(url + "?orderBy=\"timestamp\"&limitToLast=10")
    if response.status_code == 200:
        logs = response.json()
        if not logs:
            print("No logs found.")
            return
        
        # Sort logs by timestamp
        sorted_logs = sorted(logs.values(), key=lambda x: x.get('timestamp', 0))
        for log in sorted_logs:
            print(f"[{log.get('source', 'SYSTEM')}] {log.get('message', '')}")
    else:
        print(f"Error fetching logs: {response.status_code}")

if __name__ == "__main__":
    check_logs()
