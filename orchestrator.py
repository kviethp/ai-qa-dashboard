import os
import yaml
import requests
import json
import re
import time
import subprocess
from bug_reporter import UnifiedBugReporter
from memory_manager import MemoryManager
from cloud_sync import FirebaseSync
import firebase_admin
from firebase_admin import credentials, db
from typing import Dict, List, Optional
import concurrent.futures
from datetime import datetime
from dotenv import load_dotenv
import glob
import ast
import sys
import queue
import threading
# Khắc phục lỗi charmap trên Windows khi in tiếng Việt
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

class BrainManager:
    def __init__(self, ollama_host: str):
        self.ollama_host = ollama_host
        self.session = requests.Session()
        self.brain_mode = os.getenv("BRAIN_MODE", "LOCAL").upper() # LOCAL or REMOTE
        self.api_key = os.getenv("REMOTE_API_KEY", "")
        self.base_url = os.getenv("REMOTE_BASE_URL", "https://nexai.newdev.net/api/v1")
        self.remote_model = os.getenv("REMOTE_MODEL", "gpt-4o-mini")

    def query(self, prompt: str, model: str, stream_callback=None) -> str:
        """Hỏi LLM tùy theo mode hiện tại."""
        if self.brain_mode == "REMOTE" and self.api_key:
            return self._query_remote(prompt, self.remote_model, stream_callback)
        else:
            return self._query_local(prompt, model, stream_callback)

    def _query_local(self, prompt: str, model: str, stream_callback=None) -> str:
        try:
            response = self.session.post(
                f"{self.ollama_host}/api/generate",
                json={"model": model, "prompt": prompt, "stream": True},
                stream=True
            )
            full_res = ""
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line)
                    text = chunk.get("response", "")
                    full_res += text
                    if stream_callback: stream_callback(text)
            return full_res
        except Exception as e:
            return f"Error Local LLM: {e}"

    def _query_remote(self, prompt: str, model: str, stream_callback=None) -> str:
        try:
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "stream": True}
            
            print(f"📡 [Remote Brain] Connecting to {self.base_url}...")
            response = self.session.post(f"{self.base_url}/chat/completions", headers=headers, json=payload, stream=True, timeout=15)
            
            full_res = ""
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8').strip()
                    if not decoded_line.startswith("data: "):
                        continue
                        
                    line_str = decoded_line.replace('data: ', '')
                    if line_str == "[DONE]": break
                    
                    try:
                        chunk = json.loads(line_str)
                        if 'choices' in chunk and len(chunk['choices']) > 0:
                            text = chunk['choices'][0].get('delta', {}).get('content', '')
                            if text:
                                full_res += text
                                if stream_callback: stream_callback(text)
                    except json.JSONDecodeError:
                        continue
            
            if not full_res:
                print("⚠️ [Remote Brain] Warning: Empty response from API.")
            return full_res
        except Exception as e:
            print(f"❌ [Remote Brain] Error: {e}")
            return f"Error Remote API: {e}"

class TelegramManager:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.last_update_id = 0
        self.queue = queue.Queue()
        self.session = requests.Session()
        
        if self.token and self.chat_id:
            # Khởi chạy worker thread để gửi tin nhắn tuần tự
            self.stop_event = threading.Event()
            self.worker = threading.Thread(target=self._msg_worker, daemon=True)
            self.worker.start()

    def _msg_worker(self):
        """Luồng xử lý hàng đợi tin nhắn, đảm bảo không vi phạm Rate Limit."""
        while not self.stop_event.is_set():
            try:
                task = self.queue.get(timeout=1)
                method = task['method']
                url = f"{self.base_url}/{method}"
                
                if method == "sendMessage":
                    self.session.post(url, json=task['data'])
                else:
                    # Gửi file (photo, video, document)
                    with open(task['file_path'], 'rb') as f:
                        files = {task['file_type']: f}
                        self.session.post(url, data=task['data'], files=files)
                
                self.queue.task_done()
                time.sleep(0.1) # Độ trễ an toàn cho Telegram
            except queue.Empty:
                continue
            except Exception as e:
                print(f"⚠️ Telegram Worker Error: {e}")

    def send_message(self, message: str):
        if not self.token or not self.chat_id: return
        self.queue.put({
            "method": "sendMessage",
            "data": {"chat_id": str(self.chat_id), "text": str(message)[:4096], "parse_mode": "Markdown"}
        })

    def send_file(self, file_path: str, caption: str = ""):
        """Đẩy yêu cầu gửi file vào hàng đợi."""
        if not self.token or not self.chat_id or not os.path.exists(file_path): return
        file_type = "photo" if file_path.lower().endswith(('.png', '.jpg', '.jpeg')) else "video" if file_path.lower().endswith(('.mp4', '.webm')) else "document"
        self.queue.put({
            "method": f"send{file_type.capitalize()}",
            "file_path": file_path,
            "file_type": file_type,
            "data": {"chat_id": str(self.chat_id), "caption": caption}
        })

    def get_updates(self) -> List[Dict]:
        try:
            url = f"{self.base_url}/getUpdates?offset={self.last_update_id + 1}&timeout=30"
            response = self.session.get(url, timeout=35)
            updates = response.json().get('result', [])
            if updates:
                self.last_update_id = updates[-1]['update_id']
            return updates
        except Exception as e:
            print(f"Lỗi khi nhận tin nhắn: {str(e)}")
            return []

class QAAgentSystem:
    def __init__(self):
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.config = self._load_config()
        self.system_rules = self.config.get('system_rules', '')
        self.project_path = "D:/Agtest/playwright-automation"
        self.tg = TelegramManager(
            os.getenv("TELEGRAM_BOT_TOKEN", ""),
            os.getenv("TELEGRAM_CHAT_ID", "")
        )
        self.bug_reporter = UnifiedBugReporter()
        self.memory = MemoryManager()
        self.cloud_sync = FirebaseSync()
        self.status_file = r"D:\Project AI QA team\dashboard\public\agent_status.json"
        self.state_file = r"D:\Project AI QA team\state.json"
        
        # Thân não điều khiển LLM
        self.brain = BrainManager(self.ollama_host)
        
        # Locks để bảo vệ tài liệu dùng chung khi chạy song song
        self.state_lock = threading.Lock()
        self.status_lock = threading.Lock()
        
        # [Phase 3] Event để dừng toàn bộ test đang chạy (Thread-safe)
        self.stop_event = threading.Event()
        self.awaiting_resume = False
        
        # Load previous state if exists (Fault Tolerance)
        self.current_state = self._load_state()
        self._init_status()

    def _load_state(self) -> Dict:
        """Đọc trạng thái (để phục hồi sau crash) với Lock an toàn."""
        with self.state_lock:
            try:
                if os.path.exists(self.state_file):
                    with open(self.state_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if content.strip():
                            return json.loads(content)
            except Exception as e:
                print(f"⚠️ Không thể đọc state file: {e}")
            return {"current_task": None, "step": "idle", "data": {}}

    def _save_state(self, step: str, data: Dict = None):
        """Lưu lại trạng thái hiện tại với Lock an toàn."""
        with self.state_lock:
            self.current_state["step"] = step
            if data:
                self.current_state["data"].update(data)
            try:
                with open(self.state_file, 'w', encoding='utf-8') as f:
                    json.dump(self.current_state, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

    def _init_status(self):
        initial_status = {
            "ba_agent": {"status": "idle", "message": "Sẵn sàng"},
            "lead_qa": {"status": "idle", "message": "Sẵn sàng"},
            "automation": {"status": "idle", "message": "Sẵn sàng"},
            "reviewer": {"status": "idle", "message": "Sẵn sàng"},
            "secretary": {"status": "idle", "message": "Sẵn sàng"}
        }
        self._write_status(initial_status)

    def _update_agent_status(self, agent: str, status: str, message: str):
        with self.status_lock:
            try:
                if os.path.exists(self.status_file):
                    with open(self.status_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                else:
                    data = {}
                data[agent] = {"status": status, "message": message}
                
                with open(self.status_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                self.cloud_sync.sync_status(data)
            except Exception:
                pass

    def _write_status(self, data):
        with self.status_lock:
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.cloud_sync.sync_status(data)

    def _load_config(self) -> Dict:
         with open('prompts.yaml', 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _build_repository_map(self) -> str:
        """Trích xuất Class, Method, Params và JSDoc để AI hiểu sâu nghiệp vụ."""
        repo_map = []
        pages_dir = os.path.join(self.project_path, "e2e", "pages")
        
        if not os.path.exists(pages_dir):
            return "No pages directory found."
            
        for filepath in glob.glob(f"{pages_dir}/**/*.ts", recursive=True):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    file_content = f.read()
                
                # Regex trích xuất Class
                class_match = re.search(r'export\s+class\s+(\w+)', file_content)
                if class_match:
                    rel_path = os.path.relpath(filepath, self.project_path)
                    cls_name = class_match.group(1)
                    repo_map.append(f"File: {rel_path} | Class: {cls_name}")
                    
                    # Regex trích xuất Method kèm JSDoc (Comment phía trên hàm)
                    # Tìm các block: /** ... */ async method(...)
                    method_blocks = re.findall(r'(\/\*\*.*?\*\/)?\s*(async\s+\w+\s*\(.*?\))', file_content, re.DOTALL)
                    
                    if method_blocks:
                        repo_map.append("    Available Methods:")
                        for doc, signature in method_blocks[:15]:
                            clean_sig = re.sub(r'\s+', ' ', signature).strip()
                            clean_doc = ""
                            if doc:
                                # Lấy dòng mô tả ngắn trong JSDoc
                                doc_match = re.search(r'\*\s*(.*?)\n', doc)
                                if doc_match:
                                    clean_doc = f" // {doc_match.group(1).strip()}"
                            repo_map.append(f"      - {clean_sig}{clean_doc}")
            except Exception:
                pass
        return "\n".join(repo_map)

    def _get_business_context(self, task_description: str) -> str:
        """Đọc sổ tay nghiệp vụ liên quan đến task."""
        docs_dir = os.path.join(self.project_path, "docs", "business_flows")
        if not os.path.exists(docs_dir):
            return ""
            
        # Tìm file .md có tên gần giống với task hoặc keyword
        keywords = re.findall(r'\b\w+\b', task_description.lower())
        for filepath in glob.glob(f"{docs_dir}/*.md"):
            filename = os.path.basename(filepath).lower()
            if any(kw in filename for kw in keywords if len(kw) > 3):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return f"--- SỔ TAY NGHIỆP VỤ ({filename}) ---\n{f.read()}\n"
        return ""

    def _get_relevant_context(self, task_description: str) -> str:
        """Tối ưu hóa ngữ cảnh với Repository Map và Selector RAG."""
        context_str = ""
        biz_context = self._get_business_context(task_description)
        if biz_context: context_str += biz_context
            
        repo_map = self._build_repository_map()
        context_str += f"\n--- BẢN ĐỒ DỰ ÁN (Project Map) ---\n{repo_map}\n"
        
        # [Expert Gold Standard] Tự động nạp Quy tắc Expert
        expert_rules_path = f"{self.project_path}/e2e/docs/expert-rules.md"
        readme_path = f"{self.project_path}/README.md"
        
        for rule_path in [expert_rules_path, readme_path]:
            if os.path.exists(rule_path):
                filename = os.path.basename(rule_path)
                with open(rule_path, 'r', encoding='utf-8') as f:
                    context_str += f"\n--- TIÊU CHUẨN VÀNG ({filename}) ---\n{f.read()}\n"
        
        # [Expert Upgrade] Selector RAG (Simple)
        selectors_path = f"{self.project_path}/e2e/utils/selectors.ts"
        if os.path.exists(selectors_path):
            with open(selectors_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            task_keywords = re.findall(r'\b\w{4,}\b', task_description.lower())
            relevant_lines = []
            blocks = re.split(r'(export\s+const|const)', content)
            for block in blocks:
                if any(kw in block.lower() for kw in task_keywords):
                    relevant_lines.append(block)
            
            if relevant_lines:
                context_str += f"\n--- SELECTORS LIÊN QUAN (RAG Filtered) ---\n{''.join(relevant_lines[:10])}\n"
            else:
                context_str += f"\n--- TỪ ĐIỂN SELECTORS (Trích đoạn) ---\n{content[:500]}...\n"
                
        return context_str

    def ask_agent(self, agent_name: str, user_input: str, additional_context: Optional[str] = None) -> Dict[str, str]:
        agent_cfg = self.config['agents'].get(agent_name)
        ctx_str = self._get_relevant_context(user_input)
        
        # [Expert Upgrade] Lấy trí nhớ từ quá khứ
        past_exp = self.memory.query_experience(user_input)
        if past_exp:
            ctx_str += past_exp

        if additional_context:
            ctx_str += f"\n--- ADDITIONAL CONTEXT ---\n{additional_context}"

        self._update_agent_status(agent_name, "working", f"Đang xử lý: {user_input[:30]}...")

        model = os.getenv(f"{agent_name.upper()}_MODEL")
        if not model:
            model = "qwen2.5-coder:14b" if agent_name == "automation" else "qwen2.5:14b"

        prompt = (
            f"SYSTEM RULES:\n{self.system_rules}\n\n"
            f"YOUR ROLE: {agent_cfg['role']}\n"
            f"YOUR OBJECTIVE: {agent_cfg['objective']}\n"
            f"CONTEXT:\n{ctx_str}\n\n"
            f"TASK: {user_input}\n\n"
            f"Hãy bắt đầu bằng thẻ <thought> để suy luận, sau đó đưa ra kết quả cuối cùng."
        )
        
        try:
            print(f"🤖 [Agent: {agent_name}] Mode: {self.brain.brain_mode} | Đang gửi request...", flush=True)
            
            current_thought_buffer = [""] # Dùng list để pass by reference cho callback
            in_thought = [False]

            def stream_proc(text):
                print(text, end="", flush=True) # Hiện thực stream ngay trên console
                # Stream log visualization for <thought>
                if "<thought>" in text:
                    in_thought[0] = True
                elif "</thought>" in text:
                    in_thought[0] = False
                    if current_thought_buffer[0].strip():
                        self.cloud_sync.push_log(agent_name, f"🧠 {current_thought_buffer[0].strip()}")
                        current_thought_buffer[0] = ""
                elif in_thought[0]:
                    current_thought_buffer[0] += text
                    if len(current_thought_buffer[0]) > 50:
                        self.cloud_sync.push_log(agent_name, f"🧠 {current_thought_buffer[0].strip()}...")
                        current_thought_buffer[0] = ""

            raw_res = self.brain.query(prompt, model, stream_callback=stream_proc)
            
            thought = ""
            final_content = raw_res
            match = re.search(r'<thought>(.*?)</thought>', raw_res, re.DOTALL)
            if match:
                thought = match.group(1).strip()
                final_content = re.sub(r'<thought>.*?</thought>', '', raw_res, flags=re.DOTALL).strip()
            
            with open("/tmp/raw_response.txt", "w", encoding="utf-8") as f:
                f.write(raw_res) # Write the original raw_res before stripping thought tags
            
            self._update_agent_status(agent_name, "idle", "Hoàn tất")
            self.cloud_sync.push_log(agent_name, "✅ Xong!")
            
            # [Expert Upgrade] Robust JSON Extracting v3 (Foolproof)
            clean_response = str(final_content).strip()
            
            # 1. Tìm khối JSON (ưu tiên bọc trong ```json)
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', clean_response, re.DOTALL)
            if not json_match:
                json_match = re.search(r'(\{.*?\})', clean_response, re.DOTALL)

            json_data = None
            if json_match:
                try:
                    json_data = json.loads(json_match.group(1).strip())
                except:
                    pass

            # 2. Tìm khối Code
            extracted_code = ""
            if json_data and 'code_changes' in json_data:
                extracted_code = json_data['code_changes']
            else:
                # Tìm tất cả khối triple backticks
                blocks = re.findall(r'```(?:typescript|ts|javascript|js)?\s*(.*?)```', clean_response, re.DOTALL)
                if blocks:
                    # Lấy khối dài nhất (thường là code chính) hoặc nối lại
                    extracted_code = "\n\n".join(blocks)
                else:
                    # Fallback cuối cùng: Nếu không có backticks, có thể toàn bộ response là code
                    # nhưng ta sẽ lọc bỏ các dòng rác kiểu ### hoặc **
                    lines = [l for l in clean_response.split('\n') if not l.strip().startswith(('###', '**', '==='))]
                    extracted_code = "\n".join(lines).strip()

            # 3. Hậu xử lý: Gọt sạch tàn dư Markdown và comment file giả
            # Gỡ thẻ backticks lồng nhau (nếu có)
            extracted_code = re.sub(r'```.*?```', '', extracted_code, flags=re.DOTALL).strip()
            # Gỡ các dòng giả lập đường dẫn file thường thấy ở AI (// File: ...)
            extracted_code = re.sub(r'^\s*//\s*(?:File|Path|Location):.*?\n', '', extracted_code, flags=re.IGNORECASE | re.MULTILINE)
            
            print(f"📏 [Logic v3] Extracted Code Length: {len(extracted_code)}", flush=True)

            return {
                "thought": thought, 
                "response": final_content,
                "json_data": json_data,
                "extracted_code": extracted_code
            }
        except Exception as e:
            self.cloud_sync.push_log(agent_name, f"❌ Lỗi: {str(e)}")
            return {"thought": "Error", "response": f"Lỗi: {str(e)}", "json_data": None}

    def run_playwright_test(self, file_path: str) -> Dict[str, str]:
        """Thực thi test thật và lấy kết quả từ terminal dạng Stream."""
        print(f"🚀 [Execution] Đang chạy test: {file_path}...")
        self._update_agent_status("automation", "testing", f"Đang chạy {file_path}...")
        self.cloud_sync.push_log("system", f"🚀 Bắt đầu npx playwright test {file_path}")
        
        try:
            process = subprocess.Popen(
                ['npx', 'playwright', 'test', file_path],
                cwd=self.project_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding='utf-8',
                shell=True,
                bufsize=1
            )
            
            output_log = ""
            for line in iter(process.stdout.readline, ''):
                if line:
                    output_log += line
                    clean_line = line.strip()
                    if clean_line:
                        self.cloud_sync.push_log("playwright", f"🖥️ {clean_line}")
            
            if process.stdout:            
                process.stdout.close()
            process.wait()
            
            return {
                "status": "PASS" if process.returncode == 0 else "FAIL",
                "output": output_log
            }
        except Exception as e:
            error_trace = str(e)
            self.cloud_sync.push_log("system", f"❌ Lỗi hệ thống nghiêm trọng: {error_trace}")
            self.tg.send_message(f"🚨 *SYSTEM ALERT:* Phát hiện lỗi hạ tầng. Đang gọi **SRE Agent (Dr. Gear)** đến cấp cứu...")
            sre_analysis = self.ask_agent('sre_agent', f"Hệ thống vừa văng lỗi Python/OS khi chạy Playwright test script. Hãy phân tích lỗi sau và đưa ra đoạn script khắc phục (Hotfix) hoặc lệnh terminal cụ thể (ví dụ: pip install).\n\nLỗi: {error_trace}")
            
            self.tg.send_message(f"🛠️ *SRE Agent:* \n{sre_analysis['response'][:1000]}...")
            # [Optional Auto-execution of Hotfix could be added here later]
            
            return {"status": "SYSTEM_ERROR", "output": error_trace}

    def _get_failure_artifacts(self, test_name: str) -> Dict[str, str]:
        """Tìm kiếm screenshot và video trong thư mục test-results."""
        artifacts = {"screenshot": "", "video": ""}
        results_dir = f"{self.project_path}/e2e/artifacts"
        if os.path.exists(results_dir):
            for root, dirs, files in os.walk(results_dir):
                for file in files:
                    if file.endswith(".png") and "fail" in file.lower():
                        artifacts["screenshot"] = os.path.join(root, file)
                    if file.endswith(".webm") or file.endswith(".mp4"):
                        artifacts["video"] = os.path.join(root, file)
        return artifacts

    def run_expert_qa_cycle(self, task_description: str, extra_context: str = ""):
        # Check if we should resume
        if self.current_state.get("step") != "idle" and self.current_state.get("step") != "start":
            self.tg.send_message(f"🔄 *Sofia:* Em phát hiện phiên làm việc dở dang tại bước `{self.current_state['step']}`. Em sẽ tự động phục hồi nhé!")
            self.cloud_sync.push_log("system", f"🔄 Phục hồi tự động trạng thái: {self.current_state['step']}")

        self._save_state("start", {"task": task_description, "context": extra_context})

        # 0. BA Agent Phân tích requirements
        if extra_context:
            if self.current_state.get("step") == "requirements_approved":
                task_description = self.current_state["data"].get("refined_task", task_description)
                self.cloud_sync.push_log("system", "🔄 Phục hồi: Lấy Requirements đã duyệt.")
            else:
                self._save_state("analyzing_req", {})
                self.cloud_sync.push_log("system", "🔎 BA Agent (Sofia) đang phân tích tài liệu...")
                self._update_agent_status("ba_agent", "working", "Đang phân tích tài liệu...")
                
                ba_prompt = f"Phân tích tài liệu sau và trích xuất danh sách các Test Scenarios / AC ngắn gọn:\n{extra_context}"
                ba_res = self.ask_agent('ba_agent', ba_prompt)
                
                extracted_reqs = ba_res['response']
                self.cloud_sync.push_log("system", "⏳ Tạm dừng: Đang chờ duyệt Requirements trên Dashboard...")
                self._update_agent_status("ba_agent", "waiting", "Đang chờ duyệt Requirement...")
                
                while True:
                    status, feedback = self.cloud_sync.request_approval(
                        approval_type="REQUIREMENT_REVIEW",
                        task_name="Duyệt Yêu cầu",
                        content=extracted_reqs
                    )
                    if status == "approved":
                        self.cloud_sync.push_log("system", "✅ Requirements đã duyệt!")
                        self._update_agent_status("ba_agent", "idle", "Sẵn sàng")
                        task_description += f"\n\n--- DANH SÁCH YÊU CẦU ĐÃ DUYỆT ---\n{extracted_reqs}"
                        self._save_state("requirements_approved", {"refined_task": task_description})
                        break
                    elif status == "rejected":
                        self._update_agent_status("ba_agent", "working", "Đang sửa lại...")
                        extracted_reqs = self.ask_agent('ba_agent', f"User yêu cầu sửa: {feedback}\nCũ: {extracted_reqs}")['response']

        # 1. Lead QA Lập kế hoạch
        if self.current_state.get("step") == "planning_approved":
            plan_content = self.current_state["data"].get("plan_content", "")
            self.cloud_sync.push_log("system", "🔄 Phục hồi kế hoạch đã duyệt.")
        else:
            self._save_state("planning", {})
            lead_res = self.ask_agent('lead_qa', f"Lập kế hoạch test cho: {task_description}")
            plan_content = lead_res['response']
            self.tg.send_message(f"📜 *Kế hoạch:* Đã sẵn sàng. Chờ duyệt...")
            
            while True:
                tg_msg = f"🛎️ *DUYỆT KẾ HOẠCH*\n\n{plan_content[:1000]}...\n---\n✅ Duyệt | ❌ Sửa <feedback>"
                self.tg.send_message(tg_msg)
                status, feedback = self.cloud_sync.request_approval(
                    approval_type="TEST_PLAN",
                    task_name=f"Kế hoạch: {task_description[:30]}",
                    content=plan_content
                )
                if status == "approved":
                    self.tg.send_message("✅ Đã DUYỆT kế hoạch!")
                    self._update_agent_status("lead_qa", "idle", "Sẵn sàng")
                    self._save_state("planning_approved", {"plan_content": plan_content})
                    break
                elif status == "rejected":
                    self._update_agent_status("lead_qa", "working", "Đang sửa kế hoạch...")
                    plan_content = self.ask_agent('lead_qa', f"Lý do sửa: {feedback}\nKế hoạch cũ: {plan_content}")['response']

        # 2. Coder & Failure Analyzer Auto-healing
        current_code = ""
        success = False
        last_failure_output = ""
        from failure_analyzer import FailureAnalyzer
        self.analyzer = FailureAnalyzer()
        
        for attempt in range(1, 4): # 3 attempts
            self.cloud_sync.push_log("system", f"🤖 Coder đang chuẩn bị... (Lần {attempt})")
            
            repair_hint = ""
            if attempt > 1:
                self.cloud_sync.push_log("system", "🔍 Failure Analyzer đang mổ xẻ lỗi...")
                analysis_res = self.analyzer.analyze(last_failure_output)
                repair_hint = f"\n--- PHÂN TÍCH LỖI VÀ HƯỚNG SỬA (DEBUG BLUEPRINT) ---\n{analysis_res}"

            base_prompt = (
                f"Viết code Playwright cho task: {task_description}\n"
                f"Kế hoạch: {plan_content}\n"
                f"Lần thử: {attempt}\n"
                f"{repair_hint}\n\n"
                f"TRẢ VỀ JSON: {{\"change_summary\": \"...\", \"root_cause_analysis\": \"...\", \"code_changes\": \"...\"}}"
            )
            
            structured_prompt = base_prompt
            # [Meta Prompting Phase] Nếu fail lần 1, dùng Meta-Agent tối ưu lại Prompt cho Coder
            if attempt > 1:
                self.cloud_sync.push_log("system", "🧠 Meta-Prompting Agent đang vi chỉnh lại Prompt cho Coder...")
                meta_res = self.ask_agent('meta_prompting_agent', f"Với vai trò Meta-Prompt Engineer, hãy đọc Prompt gốc và Bản thiết kế sửa lỗi (Debug Blueprint) dưới đây. Hãy viết lại toàn bộ cấu trúc Prompt sao cho Thuyết Phục, Rõ Ràng và Đặc Trị nhất để AI Coder không bao giờ mắc lại lỗi cũ. Giữ nguyên yêu cầu TRẢ VỀ JSON:\n\n{base_prompt}")
                structured_prompt = meta_res['response']
                self.cloud_sync.push_log("meta_prompt", f"✨ Đã sinh ra Prompt thần thánh mới!")
            
            auto_res = self.ask_agent('automation', structured_prompt)
            current_code = auto_res.get('extracted_code', '')
            
            coder_data = auto_res.get('json_data')
            if coder_data:
                approval_content = f"**Lần {attempt}**\n**Root Cause:** {coder_data.get('root_cause_analysis','')}\n**Code:**\n```typescript\n{current_code}\n```"
            else:
                approval_content = f"**⚠️ Cảnh báo: AI không trả về JSON chuẩn**\n\n{current_code[:1000]}..."

            self._update_agent_status("automation", "waiting", f"Đang chờ duyệt Code (Lần {attempt})...")
            self.tg.send_message(f"🛠️ *Coding:* Phương án lần {attempt} đã sẵn sàng.")
            
            status, feedback = self.cloud_sync.request_approval(
                approval_type="CODE_REVIEW",
                task_name=f"Code Lần {attempt}",
                content=approval_content
            )
            
            if status == "rejected":
                task_description += f"\n[FEEDBACK LẦN {attempt}]: {feedback}"
                continue

            temp_test_path = "e2e/tests/ai_generated.spec.ts"
            full_path = os.path.join(self.project_path, temp_test_path)
            print(f"💾 Writing code to: {full_path} (Length: {len(current_code)})", flush=True)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(current_code)
                
            run_res = self.run_playwright_test(temp_test_path)
            
            if run_res['status'] == "PASS":
                self.tg.send_message(f"✅ *Victory:* Tuyệt vời Anh ơi, lần {attempt} đã PASS!")
                success = True
                break
            else:
                last_failure_output = run_res['output']
                self.tg.send_message(f"❌ *Fail lần {attempt}:* Đang tự chữa lành...")

        # 3. Bug Reporting 100% Visual
        if not success:
            artifacts = self._get_failure_artifacts("ai_generated")
            bug_report_data = self.ask_agent('lead_qa', f"Viết báo cáo lỗi chi tiết. Log: {last_failure_output[-1000:]}")
            bug_report = bug_report_data['response']
            
            self.tg.send_message(f"🚨 *PHÁT HIỆN LỖI:* \n{bug_report}")
            
            # Gửi hình ảnh/video lỗi thực tế (10% cuối cùng)
            if artifacts["screenshot"]:
                self.tg.send_file(artifacts["screenshot"], caption="📸 Screenshot màn hình lúc lỗi")
            if artifacts["video"]:
                self.tg.send_file(artifacts["video"], caption="🎥 Video quá trình xảy ra lỗi")

            self.bug_reporter.report_everywhere(f"AI Bug: {task_description[:30]}", bug_report)

        # 4. Review & Memory
        if success:
            review_res = self.ask_agent('reviewer', f"Review code: {current_code}")
            self.memory.store_experience(task_description, current_code)
            self.ask_agent('lead_qa', f"Cập nhật tài liệu cho: {task_description}")

        report = self.ask_agent('secretary', f"Tổng kết task: {task_description}")
        self.tg.send_message(f"🎁 *Tổng kết:* \n{report['response']}")

    def start_listening(self, wait=True):
        print("💓 [Thư ký Em] Đang lắng nghe Anh Việt...")
        
        # [Phase 3] Resume Intelligence
        if self.current_state.get("current_task"):
            old_task = self.current_state["current_task"]
            self.awaiting_resume = True
            msg = f"🔔 *Sofia báo cáo:* Em phát hiện có task đang dở từ lần trước: \n\n`{old_task}`\n\nAnh Việt có muốn em **tiếp tục** chiến dịch này không ạ? (Gửi 'OK' để tiếp tục hoặc 'Hủy' để xóa)"
            self.tg.send_message(msg)
        else:
            self.tg.send_message("💖 Em đã sẵn sàng phục vụ Anh Việt!")
        
        self.cloud_sync.listen_for_commands(self.process_user_input)
        
        def tg_loop():
            while True:
                try:
                    updates = self.tg.get_updates()
                    for update in updates:
                        if 'message' in update and 'text' in update['message']:
                            user_text = update['message']['text']
                            if str(update['message']['chat']['id']) == self.tg.chat_id:
                                self.process_user_input(user_text)
                except Exception as e:
                    print(f"⚠️ Telegram loop error: {e}")
                time.sleep(2)
        
        listener_thread = threading.Thread(target=tg_loop, daemon=True)
        listener_thread.start()
        
        if wait:
            while True: time.sleep(1)

    def process_user_input(self, text: str, context: str = "", target_agent: Optional[str] = None):
        text_lower = text.lower().strip()
        
        # 1. [Phase 3] Lệnh Dừng Khẩn Cấp (Global Stop)
        if any(kw in text_lower for kw in ["dừng", "stop", "cancel", "huỷ", "hủy"]):
            self.stop_event.set()
            self.tg.send_message("🛑 *LỆNH DỪNG:* Đang yêu cầu các Agent rút lui và dọn dẹp chiến trường... Vui lòng đợi trong giây lát!")
            self._save_state("idle", {"current_task": None})
            # Reset event sau 5s để có thể nhận lệnh mới
            threading.Timer(5, self.stop_event.clear).start()
            self.awaiting_resume = False
            return

        # 2. [Phase 3] Xử lý Resume Confirmation
        if self.awaiting_resume:
            if any(kw in text_lower for kw in ["ok", "tiếp", "đồng ý", "yes"]):
                self.awaiting_resume = False
                task = self.current_state["current_task"]
                self.tg.send_message(f"🫡 Tuân lệnh! Em tiếp tục chiến dịch: `{task}`")
                threading.Thread(target=self.process_user_input, args=(task,)).start()
                return
            elif any(kw in text_lower for kw in ["huỷ", "hủy", "không", "no", "reject"]):
                self.awaiting_resume = False
                self._save_state("idle", {"current_task": None})
                self.tg.send_message("🗑️ Đã xoá bỏ task cũ. Em sẵn sàng cho nhiệm vụ mới!")
                return
            else:
                self.tg.send_message("👉 Anh ơi, xác nhận giúp em task cũ ('OK' hoặc 'Hủy') trước khi ra lệnh mới nhé!")
                return

        is_approval = any(kw in text_lower for kw in ["duyệt", "ok", "đồng ý"])
        is_rejection = any(kw in text_lower for kw in ["sửa", "không", "reject"]) and len(text_lower) > 2

        if is_approval or is_rejection:
            try:
                ref = self.cloud_sync.db.reference('approvals/current')
                data = ref.get()
                if data and data.get('status') == 'pending':
                    new_status = 'approved' if is_approval else 'rejected'
                    ref.update({'status': new_status, 'feedback': text if is_rejection else ""})
                    self.tg.send_message(f"🫡 Đã ghi nhận sếp {new_status.upper()} qua Telegram!")
                    return
            except Exception: pass

        if target_agent and target_agent in self.config['agents']:
            res = self.ask_agent(target_agent, text, additional_context=context)
            self.cloud_sync.push_log(target_agent, f"🤖 Phản hồi: {res['response']}")
            return

        intent_res = self.ask_agent('secretary', f"Phân tích ý định: '{text}'. Bắt đầu bằng TASK: hoặc CHAT:")
        res_text = intent_res['response']
        
        if "TASK:" in res_text.upper():
            task_raw = res_text.split("TASK:")[1].strip() if "TASK:" in res_text.upper() else text
            
            # [Parallel Phase] Phân rã task lớn thành danh sách test cases
            self.cloud_sync.push_log("system", f"🪓 Đang gọt giũa Task: '{task_raw}'")
            split_res = self.ask_agent('ba_agent', f"Với Task lớn sau đây: '{task_raw}'. Hãy chia nhỏ nó thành một danh sách các luồng Test độc lập (mỗi luồng là 1 chức năng/màn hình cụ thể). Trả về CHỈ danh sách các gạch đầu dòng (ví dụ: '- Test màn hình A\n- Test màn hình B'). Nếu task đơn giản chỉ có 1 chức năng thì trả về đúng 1 gạch đầu dòng.")
            sub_tasks = [t.strip().strip('-').strip() for t in split_res['response'].split('\n') if t.strip().startswith('-')]
            
            if not sub_tasks:
                sub_tasks = [task_raw]
                
            self.tg.send_message(f"🚀 *Parallel Execution:* Em đã chia task này thành {len(sub_tasks)} luồng chạy độc lập! Đang huy động đội quân Automation... ⚔️")
            
            # Khởi tạo ThreadPool để chạy các Sub-Tasks song song
            max_agents = 3 # Giới hạn 3 luồng để tránh quá tải VRAM (có thể config vào .env sau)
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_agents) as executor:
                # Dùng list comprehension kết hợp lambda để chạy hàm (truyền task con vào)
                futures = {executor.submit(self.run_expert_qa_cycle, sub_task, context): sub_task for sub_task in sub_tasks}
                for future in concurrent.futures.as_completed(futures):
                    sub_task = futures[future]
                    try:
                        # Kết quả trả về của một cycle (Có thể sửa run_expert_qa_cycle để return status Pass/Fail sau này)
                        future.result() 
                        self.cloud_sync.push_log("system", f"🏁 Sub-task hoàn thành: {sub_task}")
                    except Exception as e:
                        self.cloud_sync.push_log("system", f"💥 Sub-task '{sub_task}' sụp đổ trong thread: {e}")
            
            self.tg.send_message(f"🏆 *Chiến dịch kết thúc:* Toàn bộ {len(sub_tasks)} luồng Automation đã hoàn thành!")
        else:
            self.tg.send_message(res_text.replace("CHAT:", "").strip())

if __name__ == "__main__":
    system = QAAgentSystem()
    if len(sys.argv) > 1:
        # Chế độ chạy trực tiếp task, nhưng vẫn bật listener ở background để nhận lệnh STOP
        task = " ".join(sys.argv[1:])
        system.start_listening(wait=False)
        system.process_user_input(task)
        # Đợi các thread hoàn thành hoặc bị stop
        while any(t.is_alive() for t in threading.enumerate() if t.name != "MainThread" and not t.daemon):
            time.sleep(1)
    else:
        # Chế độ nghỉ chờ lệnh
        system.start_listening(wait=True)
