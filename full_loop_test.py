from orchestrator import QAAgentSystem
import os
from dotenv import load_dotenv

load_dotenv()
os.environ["AUTO_APPROVE"] = "true"

print("--- FULL AUTOMATED QA CYCLE START ---")
system = QAAgentSystem()
task = "Tạo và chạy test case: Quản lý người dùng -> Thêm mới người dùng"

# Force cleanup state to avoid resume loops if skip is needed
system.current_state = {"step": "idle", "data": {}}

system.process_user_input(task)
print("--- FULL AUTOMATED QA CYCLE END ---")
