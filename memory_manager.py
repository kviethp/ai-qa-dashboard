import os
import chromadb
import sys
from chromadb.config import Settings
from typing import List, Dict

# Fix charmap error on Windows
if sys.platform == "win32":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

class MemoryManager:
    def __init__(self, db_path: str = "./memory_db"):
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name="qa_experience")

    def store_experience(self, task: str, solution: str, metadata: Dict = {}):
        """Lưu trữ một giải pháp thành công vào trí nhớ."""
        self.collection.add(
            documents=[f"Task: {task}\nSolution: {solution}"],
            metadatas=[metadata],
            ids=[f"task_{len(self.collection.get()['ids']) + 1}"]
        )
        print(f"🧠 [Memory] Đã ghi nhớ giải pháp cho: {task[:50]}...")

    def query_experience(self, task_description: str, n_results: int = 1) -> str:
        """Truy xuất các trải nghiệm liên quan từ quá khứ."""
        try:
            results = self.collection.query(
                query_texts=[task_description],
                n_results=n_results
            )
            if results['documents'] and len(results['documents'][0]) > 0:
                print(f"🧠 [Memory] Đã tìm thấy {len(results['documents'][0])} trải nghiệm liên quan.")
                return "\n--- PAST EXPERIENCE ---\n" + "\n".join(results['documents'][0])
            return ""
        except Exception:
            return ""

if __name__ == "__main__":
    mem = MemoryManager()
    # mem.store_experience("Viết test login", "Dùng Page Object Model...")
    # print(mem.query_experience("Cách làm login"))
