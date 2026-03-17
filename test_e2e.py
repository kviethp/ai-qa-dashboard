from orchestrator import QAAgentSystem
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Fix charmap error on Windows
if sys.platform == "win32":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

def test_single_command():
    os.environ["OLLAMA_HOST"] = "http://localhost:11434"
    system = QAAgentSystem()
    print("Testing single command: 'Chạy test case cls-login-ddt.spec'")
    system.process_user_input("Chạy test case cls-login-ddt.spec")

def test_sre_agent():
    os.environ["OLLAMA_HOST"] = "http://localhost:11434"
    system = QAAgentSystem()
    print("Testing SRE Agent injection with simulated OS error...")
    try:
        # Simulate an OS error that would trigger the SRE Agent
        raise OSError("Simulated exception: [Errno 28] No space left on device: '/var/log/playwright'")
    except Exception as e:
        # Call the orchestrator logic manually to bypass subprocess for testing
        error_trace = str(e)
        system.cloud_sync.push_log("system", f"❌ Lỗi hệ thống nghiêm trọng: {error_trace}")
        system.tg.send_message(f"🚨 *SYSTEM ALERT:* Phát hiện lỗi hạ tầng. Đang gọi **SRE Agent (Dr. Gear)** đến cấp cứu...")
        sre_analysis = system.ask_agent('sre_agent', f"Hệ thống vừa văng lỗi Python/OS khi chạy Playwright test script. Hãy phân tích lỗi sau và đưa ra đoạn script khắc phục (Hotfix) hoặc lệnh terminal cụ thể (ví dụ: pip install).\n\nLỗi: {error_trace}")
        system.tg.send_message(f"🛠️ *SRE Agent:* \n{sre_analysis['response'][:1000]}...")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "sre":
        test_sre_agent()
    else:
        test_single_command()
