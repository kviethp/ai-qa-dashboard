import os
import requests
import sys
from typing import List
from dotenv import load_dotenv

load_dotenv()

# Fix charmap error on Windows
if sys.platform == "win32":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

class GitLabBugReporter:
    def __init__(self):
        self.token = os.getenv("GITLAB_API_TOKEN")
        self.project_id = os.getenv("GITLAB_PROJECT_ID")
        self.base_url = os.getenv("GITLAB_BASE_URL", "https://gitlab.com/api/v4")

    def create_issue(self, title: str, description: str, labels: list = ["bug", "ai-reported"]):
        if not self.token or not self.project_id:
            return None

        url = f"{self.base_url}/projects/{self.project_id}/issues"
        headers = {"PRIVATE-TOKEN": self.token}
        payload = {
            "title": title,
            "description": description,
            "labels": ",".join(labels)
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 201:
                return response.json().get('web_url')
            return None
        except Exception:
            return None

class JiraBugReporter:
    def __init__(self):
        self.email = os.getenv("JIRA_EMAIL")
        self.api_token = os.getenv("JIRA_API_TOKEN")
        self.server_url = os.getenv("JIRA_SERVER_URL") # e.g., https://your-domain.atlassian.net
        self.project_key = os.getenv("JIRA_PROJECT_KEY")

    def create_issue(self, title: str, description: str, issuetype: str = "Bug"):
        if not all([self.email, self.api_token, self.server_url, self.project_key]):
            return None

        url = f"{self.server_url}/rest/api/3/issue"
        auth = requests.auth.HTTPBasicAuth(self.email, self.api_token)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        # Jira Cloud dùng định dạng ADF (Atlassian Document Format) cho description, 
        # nhưng ở đây chúng ta dùng bảng Markdown đơn giản cho dễ
        payload = {
            "fields": {
                "project": {"key": self.project_key},
                "summary": title,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description}]
                        }
                    ]
                },
                "issuetype": {"name": issuetype}
            }
        }

        try:
            response = requests.post(url, json=payload, headers=headers, auth=auth)
            if response.status_code == 201:
                key = response.json().get('key')
                return f"{self.server_url}/browse/{key}"
            return None
        except Exception:
            return None

class UnifiedBugReporter:
    def __init__(self):
        self.gitlab = GitLabBugReporter()
        self.jira = JiraBugReporter()

    def report_everywhere(self, title: str, description: str) -> List[str]:
        urls = []
        gl_url = self.gitlab.create_issue(title, description)
        if gl_url: urls.append(gl_url)
        
        jr_url = self.jira.create_issue(title, description)
        if jr_url: urls.append(jr_url)
        
        return urls

if __name__ == "__main__":
    reporter = UnifiedBugReporter()
