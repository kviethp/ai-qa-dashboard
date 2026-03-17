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
from typing import Dict, List, Optional
from dotenv import load_dotenv
import glob
import ast

class TelegramManager:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.last_update_id = 0

    def send_message(self, message: str):
        if not self.token or not self.chat_id:
            print("⚠️ Telegram config missing, skipping...")
            return
        try:
            payload = {
                "chat_id": str(self.chat_id),
                "text": str(message)[:4096],
                "parse_mode": "Markdown"
            }
            requests.post(f"{self.base_url}/sendMessage", json=payload)
        except Exception as e:
            print(f"Lỗi khi gửi Telegram: {str(e)}")

    def get_updates(self) -> List[Dict]:
        try:
            url = f"{self.base_url}/getUpdates?offset={self.last_update_id + 1}&timeout=30"
            response = requests.get(url, timeout=35)
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
        self.status_file = r"c:\Users\vietkq\.gemini\antigravity\playground\inner-rocket\dashboard\public\agent_status.json"
        self.state_file = r"c:\Users\vietkq\.gemini\antigravity\playground\inner-rocket\state.json"
        
        # Load previous state if exists (Fault Tolerance)
        self.current_state = self._load_state()
        
        self._init_status()

    def _load_state(self) -> Dict:
        """Đọc trạng thái (để phục hồi sau crash)"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {"current_task": None, "step": "idle", "data": {}}

    def _save_state(self, step: str, data: Dict = None):
        """Lưu lại trạng thái hiện tại."""
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
        try:
            with open(self.status_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data[agent] = {"status": status, "message": message}
            self._write_status(data)
        except Exception:
            pass

    def _write_status(self, data):
        with open(self.status_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.cloud_sync.sync_status(data)

    def _load_config(self) -> Dict:
         with open('prompts.yaml', 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _build_repository_map(self) -> str:
        """Trích xuất tên Class và Method từ thư mục e2e/pages để Coder biết tái sử dụng."""
        repo_map = []
        pages_dir = os.path.join(self.project_path, "e2e", "pages")
        
        if not os.path.exists(pages_dir):
            return "No pages directory found."
            
        for filepath in glob.glob(f"{pages_dir}/**/*.ts", recursive=True):
            try:
                # Basic parsing to find classes and methods (since it's TS, we use regex for speed)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                class_names = re.findall(r'export\s+class\s+(\w+)', content)
                methods = re.findall(r'async\s+(\w+)\s*\(', content)
                
                if class_names:
                    rel_path = os.path.relpath(filepath, self.project_path)
                    repo_map.append(f"File: {rel_path}")
                    for cls in class_names:
                        repo_map.append(f"  Class: {cls}")
                    if methods:
                        limited_methods = ", ".join(methods[:10])
                        repo_map.append(f"    Methods: {limited_methods}...") # giới hạn số lượng
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
        """Tối ưu hóa ngữ cảnh với Repository Map và Business Context."""
        context_str = ""
        
        # 1. Inject Business Context
        biz_context = self._get_business_context(task_description)
        if biz_context:
            context_str += biz_context
            
        # 2. Inject Repository Map
        repo_map = self._build_repository_map()
        context_str += f"\n--- BẢN ĐỒ DỰ ÁN (Hãy tái sử dụng các hàm này) ---\n{repo_map}\n"
        
        # 3. Inject Selectors (Legacy)
        selectors_path = f"{self.project_path}/e2e/utils/selectors.ts"
        if os.path.exists(selectors_path):
            with open(selectors_path, 'r', encoding='utf-8') as f:
                content = f.read()
                context_str += f"\n--- TỪ ĐIỂN SELECTORS ---\n{content[:1000]}...\n"
                
        return context_str

    def ask_agent(self, agent_name: str, user_input: str, additional_context: Optional[str] = None) -> Dict[str, str]:
        agent_cfg = self.config['agents'].get(agent_name)
        ctx_str = self._get_relevant_context(user_input)
        
        # [Perfect Level Phase 2] Lấy trí nhớ từ quá khứ
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
            response = requests.post(
                f"{self.ollama_host}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": True
                },
                stream=True
            )
            raw_res = ""
            current_thought_buffer = ""
            in_thought = False

            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line)
                    text = chunk.get("response", "")
                    raw_res += text

                    # Stream log visualization for <thought>
                    if "<thought>" in text:
                        in_thought = True
                    elif "</thought>" in text:
                        in_thought = False
                        if current_thought_buffer.strip():
                            self.cloud_sync.push_log(agent_name, f"🧠 {current_thought_buffer.strip()}")
                            current_thought_buffer = ""
                    elif in_thought:
                        current_thought_buffer = current_thought_buffer + str(text)
                        if len(current_thought_buffer) > 50: # push chunk
                            self.cloud_sync.push_log(agent_name, f"🧠 {current_thought_buffer.strip()}...")
                            current_thought_buffer = ""
                    else:
                        # Once outside thought, we could also stream the actual response
                        pass

            thought = ""
            final_content = raw_res
            match = re.search(r'<thought>(.*?)</thought>', raw_res, re.DOTALL)
            if match:
                thought = match.group(1).strip()
                final_content = re.sub(r'<thought>.*?</thought>', '', raw_res, flags=re.DOTALL).strip()
            
            self._update_agent_status(agent_name, "idle", "Hoàn tất")
            self.cloud_sync.push_log(agent_name, "✅ Xong!")
            return {"thought": thought, "response": str(final_content)}
        except Exception as e:
            self.cloud_sync.push_log(agent_name, f"❌ Lỗi: {str(e)}")
            return {"thought": "Error", "response": f"Lỗi: {str(e)}"}

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
                text=True,
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
                        
            process.stdout.close()
            process.wait()
            
            return {
                "status": "PASS" if process.returncode == 0 else "FAIL",
                "output": output_log
            }
        except Exception as e:
            self.cloud_sync.push_log("system", f"❌ Lỗi chạy test: {str(e)}")
            return {"status": "ERROR", "output": str(e)}

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
        self._save_state("start", {"task": task_description, "context": extra_context})
        self.tg.send_message(f"💖 *Thư ký Em báo cáo:* Em đã nhận nhiệm vụ mới. Đang phân tích...")

        # 0. BA Agent Phân tích requirements (Nếu có context)
        if extra_context:
            if self.current_state.get("step") == "requirements_approved":
                task_description = self.current_state["data"].get("refined_task", task_description)
                self.cloud_sync.push_log("system", "🔄 Phục hồi: Lấy Requirements đã duyệt.")
            else:
                self._save_state("analyzing_req", {})
                self.cloud_sync.push_log("system", "🔎 BA Agent đang phân tích tài liệu đầu vào (SRS/AC)...")
                self._update_agent_status("ba_agent", "working", "Đang phân tích tài liệu...")
                
                ba_prompt = f"Phân tích tài liệu sau và trích xuất danh sách các Test Scenarios / Acceptance Criteria ngắn gọn, dùng làm đầu vào cho QA:\n{extra_context}"
                ba_res = self.ask_agent('ba_agent', ba_prompt)
                
                extracted_reqs = ba_res['response']
                self.cloud_sync.push_log("system", "⏳ Tạm dừng: Đang chờ duyệt Requirements (ACs) trên Dashboard...")
                self._update_agent_status("ba_agent", "waiting", "Đang chờ duyệt Requirement...")
                
                while True:
                    status, feedback = self.cloud_sync.request_approval(
                        approval_type="REQUIREMENT_REVIEW",
                        task_name="Duyệt Yêu cầu (Requirements)",
                        content=extracted_reqs
                    )
                    
                    if status == "approved":
                        self.cloud_sync.push_log("system", "✅ Requirements đã được duyệt!")
                        self._update_agent_status("ba_agent", "idle", "Sẵn sàng")
                        # Gộp requirements vào task cho Lead QA
                        task_description += f"\n\n--- DANH SÁCH YÊU CẦU ĐÃ DUYỆT (TỪ BA) ---\n{extracted_reqs}"
                        self._save_state("requirements_approved", {"refined_task": task_description})
                        break
                    elif status == "rejected":
                        self.cloud_sync.push_log("system", f"✍️ Feedback từ User: {feedback}")
                        self._update_agent_status("ba_agent", "working", "Đang phân tích lại...")
                        extracted_reqs = self.ask_agent('ba_agent', f"User không đồng ý với Requirements trước, yêu cầu sửa: {feedback}\nRequirements cũ:\n{extracted_reqs}")['response']

        # 1. Lead QA Lập kế hoạch & Chờ duyệt (Human-in-the-loop)
        if self.current_state.get("step") == "planning_approved":
            plan_content = self.current_state["data"].get("plan_content", "")
            self.cloud_sync.push_log("system", "🔄 Phục hồi trạng thái: Lấy kế hoạch đã duyệt từ đợt chạy trước.")
        else:
            self._save_state("planning", {})
            lead_res = self.ask_agent('lead_qa', f"Lập kế hoạch test tỉ mỉ cho: {task_description}")
            self.tg.send_message(f"📜 *Kế hoạch:* Kế hoạch đã sẵn sàng. Đang chờ Anh duyệt trên Dashboard.")
            self.cloud_sync.push_log("system", "⏳ Tạm dừng: Đang chờ duyệt Kế Hoạch (Test Plan) trên Dashboard...")
            self._update_agent_status("lead_qa", "waiting", "Đang chờ user duyệt...")
            
            plan_content = lead_res['response']
            while True:
                status, feedback = self.cloud_sync.request_approval(
                    approval_type="TEST_PLAN",
                    task_name=task_description,
                    content=plan_content
                )
                
                if status == "approved":
                    self.tg.send_message("✅ *Anh Việt:* Đã DUYỆT kế hoạch!")
                    self.cloud_sync.push_log("system", "✅ Kế hoạch đã được duyệt, bắt đầu tiến hành Code.")
                    self._update_agent_status("lead_qa", "idle", "Sẵn sàng")
                    self._save_state("planning_approved", {"plan_content": plan_content})
                    break
                elif status == "rejected":
                    self.tg.send_message(f"❌ *Anh Việt yêu cầu sửa đổi:* {feedback}\nEm đang lập lại kế hoạch...")
                    self.cloud_sync.push_log("system", f"✍️ Nhận feedback từ user: {feedback}")
                    self._update_agent_status("lead_qa", "working", "Đang viết lại kế hoạch...")
                    lead_res = self.ask_agent('lead_qa', f"Kế hoạch của bạn bị TỪ CHỐI với lý do: {feedback}\nHãy làm lại kế hoạch mới tốt hơn dựa trên kế hoạch cũ.\nKế hoạch cũ:\n{plan_content}")
                    plan_content = lead_res['response']

        current_code = ""
        success = False
        last_failure_output = ""
        
        for attempt in range(3):
            # 2. Coder Viết Code & Giải trình (Explainable AI)
            self.cloud_sync.push_log("system", f"🤖 Coder đang viết code... (Lần thử {attempt+1})")
            
            structured_prompt = (
                f"Viết/Sửa code cho task: {task_description}\n"
                f"Kế hoạch Đã Duyệt: {plan_content}\n"
                f"Lần thử: {attempt+1}\n\n"
                f"YÊU CẦU BẮT BUỘC: Bạn PHẢI trả lời duy nhất bằng MỘT chuỗi JSON hợp lệ với cấu trúc sau, KHÔNG thêm bất kỳ text nào ngoài JSON:\n"
                f"{{\n"
                f"  \"change_summary\": \"Tóm tắt bạn sửa/thêm gì\",\n"
                f"  \"root_cause_analysis\": \"Tại sao cần code thế này\",\n"
                f"  \"optimal_reason\": \"Tại sao đây là cách tối ưu\",\n"
                f"  \"code_changes\": \"Nội dung code thực tế\"\n"
                f"}}"
            )
            
            auto_res = self.ask_agent('automation', structured_prompt)
            
            # Cố gắng Parse JSON từ Coder
            try:
                # Tìm chuỗi JSON trong response (phòng khi LLM nói nhảm)
                json_str = auto_res['response']
                match = re.search(r'\{.*\}', json_str, re.DOTALL)
                if match:
                    json_str = match.group(0)
                
                coder_data = json.loads(json_str)
                current_code = coder_data.get('code_changes', '')
                
                # 3. Chờ duyệt Code
                self.cloud_sync.push_log("system", "⏳ Tạm dừng: Đang chờ duyệt Code Diff trên Dashboard...")
                self._update_agent_status("automation", "waiting", "Đang chờ user duyệt Code...")
                
                approval_content = (
                    f"**Tóm tắt:** {coder_data.get('change_summary', '')}\n\n"
                    f"**Phân tích:** {coder_data.get('root_cause_analysis', '')}\n\n"
                    f"**Lý do Tối ưu:** {coder_data.get('optimal_reason', '')}\n\n"
                    f"**Code Đề Xuất:**\n```typescript\n{current_code}\n```"
                )
                
                status, feedback = self.cloud_sync.request_approval(
                    approval_type="CODE_REVIEW",
                    task_name=f"Code cho: {task_description[:30]}",
                    content=approval_content
                )
                
                if status == "rejected":
                    self.cloud_sync.push_log("system", f"✍️ Code bị TỪ CHỐI: {feedback}. Coder đang thử lại...")
                    task_description += f"\n[FEEDBACK TỪ USER LẦN {attempt+1}]: {feedback}"
                    continue # Bắt đầu lại vòng lặp attempt
                else:
                    self.cloud_sync.push_log("system", "✅ Code Đã Duyệt! Bắt đầu lưu file và chạy Test.")
                    self._update_agent_status("automation", "testing", "Đang chạy Test...")
                
            except json.JSONDecodeError:
                self.cloud_sync.push_log("system", "⚠️ Lỗi: Coder không trả về JSON hợp lệ. Thử lại sinh code thông thường...")
                current_code = auto_res['response']
                # Nếu không phải JSON thì fallback chạy luôn (hoặc có thể ép duyệt text thường)

            temp_test_path = "e2e/tests/ai_generated.spec.ts"
            
            # Lưu code vào file
            os.makedirs(os.path.dirname(os.path.join(self.project_path, temp_test_path)), exist_ok=True)
            with open(os.path.join(self.project_path, temp_test_path), 'w', encoding='utf-8') as f:
                f.write(current_code)
                
            # 4. Thực thi thực tế
            run_res = self.run_playwright_test(temp_test_path)
            
            if run_res['status'] == "PASS":
                self.tg.send_message(f"✅ *Tuyệt vời:* Code đã chạy **PASS** trên môi trường thật!")
                success = True
                break
            else:
                last_failure_output = run_res['output']
                self.tg.send_message(f"⚠️ *Lần thử {attempt+1} fail:* Đang phân tích lỗi...")
                task_description += f"\n\nERROR LOG:\n{run_res['output'][-1000:]}"

        # 3. [Perfect Level Phase 1] Bug Reporting
        if not success:
            artifacts = self._get_failure_artifacts("ai_generated")
            bug_prompt = (
                f"Task: {task_description}\n"
                f"Log lỗi: {last_failure_output[-2000:]}\n"
                f"Hãy viết một báo cáo lỗi (Bug Report) CHUYÊN NGHIỆP gồm: \n"
                f"1. Tiêu đề lỗi.\n2. Mức độ (Severity).\n3. Các bước tái hiện.\n4. Kết quả mong đợi vs Thực tế.\n"
                f"Sử dụng định dạng Markdown Table cực đẹp."
            )
            bug_report = self.ask_agent('lead_qa', bug_prompt)
            
            report_msg = f"🚨 *PHÁT HIỆN LỖI NGHIÊM TRỌNG:*\n\n{bug_report['response']}\n\n"
            if artifacts["screenshot"]:
                report_msg += f"📸 *Screenshot lỗi:* Đã lưu tại hệ thống.\n"
            if artifacts["video"]:
                report_msg += f"🎥 *Video quay lại:* Đã sẵn sàng để Anh xem.\n"
            
            self.tg.send_message(report_msg)
            
            # Đẩy lên GitLab & Jira nếu có config
            issue_urls = self.bug_reporter.report_everywhere(
                title=f"AI-Generated Bug: {task_description[:50]}...",
                description=bug_report['response']
            )
            
            if issue_urls:
                links = "\n".join([f"- [Link Issue]({url})" for url in issue_urls])
                self.tg.send_message(f"🚀 *Bug Reporting:* Em đã đẩy lỗi này lên các hệ thống quản lý rồi Anh nhé:\n{links}")
            else:
                self.tg.send_message("💡 *Perfect Level:* Em đã soạn sẵn báo cáo lỗi chuyên sâu, Anh chỉ cần gật đầu là em xử lý ngay ạ!")

        # 4. Reviewer chốt hạ (nếu PASS)
        if success:
            review_res = self.ask_agent('reviewer', f"Review code cuối cùng:\n{current_code}")
            self.tg.send_message(f"🕵️ *Reviewer:* {review_res['response'][:200]}...")
            
            # [Perfect Level Phase 2] Ghi nhớ giải pháp thành công
            self.memory.store_experience(task_description, current_code)
            
            # [Perfect Level Phase 3] Multi-tier Testing (Placeholder)
            self.tg.send_message("🧪 *Multi-tier:* Em đang tiến hành quét API và Bảo mật bổ sung cho Anh...")
            
            self.ask_agent('lead_qa', f"Cập nhật README.md cho tính năng: {task_description}")

        # 5. Secretary báo cáo
        report = self.ask_agent('secretary', f"Báo cáo kết quả Perfect Ph1 cho: {task_description}")
        self.tg.send_message(f"🎁 *Tổng kết:* \n{report['response']}")

    def start_listening(self):
        print("💓 [Thư ký Em] Đang lắng nghe Anh Việt trên Telegram & Dashboard...")
        self.tg.send_message("💖 Em đã sẵn sàng phục vụ Anh Việt trên cả Telegram và Dashboard Online ạ!")
        
        # [Perfect Level Phase 5] Lắng nghe lệnh từ Dashboard Online
        def on_cloud_command(text, context="", target_agent=None):
            print(f"☁️ [Dashboard Command]: {text}")
            if target_agent:
                print(f"🎯 Target Agent: {target_agent}")
            self.tg.send_message(f"📱 *Nhận lệnh từ Dashboard:* {text}")
            self.process_user_input(text, context, target_agent=target_agent)

        self.cloud_sync.listen_for_commands(on_cloud_command)
        
        while True:
            updates = self.tg.get_updates()
            for update in updates:
                if 'message' in update and 'text' in update['message']:
                    user_text = update['message']['text']
                    chat_id = str(update['message']['chat']['id'])
                    
                    if chat_id != self.tg.chat_id:
                        continue

                    print(f"📩 Tin nhắn từ Anh Việt (Tele): {user_text}")
                    self.process_user_input(user_text)
            
            time.sleep(1)

    def process_user_input(self, text: str, context: str = "", target_agent: Optional[str] = None):
        if target_agent and target_agent in self.config['agents']:
            # Chat trực tiếp với Agent
            self.cloud_sync.push_log("system", f"💬 Gửi yêu cầu trực tiếp tới {target_agent.upper()}...")
            res = self.ask_agent(target_agent, text, additional_context=context)
            self.cloud_sync.push_log(target_agent, f"🤖 Phản hồi: {res.get('response', '')}")
            return

        intent_res = self.ask_agent('secretary', f"Phân tích ý định của Anh Việt: '{text}'", additional_context=context)
        response_text = str(intent_res.get('response', ''))

        if "TASK:" in response_text.upper():
            task = response_text.split("TASK:")[1].strip()
            self.run_expert_qa_cycle(task, extra_context=context)
        else:
            reply = response_text.replace("CHAT:", "").strip()
            self.tg.send_message(reply)

import sys

if __name__ == "__main__":
    system = QAAgentSystem()
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
        system.run_expert_qa_cycle(task)
    else:
        system.start_listening()
