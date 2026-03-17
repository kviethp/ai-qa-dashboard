import os
import requests
import sys
from dotenv import load_dotenv

load_dotenv()

# Fix charmap error on Windows
if sys.platform == "win32":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

class FailureAnalyzer:
    def __init__(self):
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = os.getenv("REVIEWER_MODEL", "qwen2.5:14b")

    def analyze(self, error_log):
        print(f"🔍 [Failure Analyzer] Đang phân tích lỗi bằng {self.model}...")
        
        prompt = (
            f"Bạn là một Senior QA Automation Expert (AI-Powered). Hãy phân tích log lỗi Playwright dưới đây và tạo ra một 'DEBUG BLUEPRINT' để hướng dẫn AI Coder sửa lỗi.\n\n"
            f"YÊU CẦU BẢN THIẾT KẾ (BLUEPRINT):\n"
            f"1. **Root Cause Analysis**: Phân tích chính xác tại sao lỗi xảy ra (do Selector thay đổi, do Network chậm, do logic code, hay do môi trường).\n"
            f"2. **Healing Strategy**: Chiến lược sửa lỗi tối ưu (ví dụ: sử dụng `waitForSelector` thay cho `waitForTimeout`, sử dụng `regex` cho selector linh hoạt hơn).\n"
            f"3. **Proposed Fix**: Đoạn mã đề xuất để vượt qua lỗi này.\n\n"
            f"Lưu ý: Bạn không viết lại toàn bộ file, chỉ tập trung vào phần bị lỗi.\n\n"
            f"--- LOG LỖI THỰC TẾ ---\n{error_log}"
        )

        try:
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            return response.json().get('response')
        except Exception as e:
            return f"Lỗi khi gọi AI phân tích: {str(e)}"

if __name__ == "__main__":
    if len(sys.argv) > 1:
        log_content = sys.argv[1]
    else:
        log_content = "Error: page.goto: Navigation timeout of 30000ms exceeded"
    
    analyzer = FailureAnalyzer()
    print(analyzer.analyze(log_content))
