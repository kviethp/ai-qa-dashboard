import requests
import os
from dotenv import load_dotenv

load_dotenv()

def fetch_logs():
    db_url = 'https://ai-qa-agents-default-rtdb.firebaseio.com/live_logs.json'
    res = requests.get(db_url)
    if res.status_code == 200:
        logs = res.json()
        if not logs:
            print("No logs found.")
            return
        # Get last 10 logs
        log_items = list(logs.values())
        sorted_logs = sorted(log_items, key=lambda x: x.get('timestamp', 0))
        for l in sorted_logs[-20:]:
            print(f"[{l.get('source', '???')}] {l.get('message', '')}")
    else:
        print(f"Error: {res.status_code}")

if __name__ == "__main__":
    fetch_logs()
