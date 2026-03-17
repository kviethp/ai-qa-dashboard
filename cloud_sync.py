import firebase_admin
from firebase_admin import credentials, db
import os
import json
import time
import sys

# Fix charmap error on Windows
if sys.platform == "win32":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

class FirebaseSync:
    def __init__(self):
        # Chúng ta sẽ sử dụng cấu hình trực tiếp hoặc file json
        # Để đơn giản cho Anh Việt, em sẽ dùng cấu hình URL trước
        self.enabled = False
        self.cred_path = "firebase-key.json"
        self.last_timestamp = 0
        
        if os.path.exists(self.cred_path):
            try:
                cred = credentials.Certificate(self.cred_path)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': 'https://ai-qa-agents-default-rtdb.firebaseio.com'
                })
                self.enabled = True
                print("✅ Firebase Cloud Sync initialized.")
            except Exception as e:
                print(f"❌ Firebase Init Error: {e}")

    def sync_status(self, data):
        if not self.enabled:
            return
        try:
            ref = db.reference('agent_status')
            ref.set(data)
        except Exception as e:
            print(f"❌ Cloud Sync Failed: {e}")

    def push_log(self, source, message):
        """Pushes a live log string to a rolling list in Firebase."""
        if not self.enabled:
            return
        try:
            # push to a specific list
            ref = db.reference('live_logs')
            new_log_ref = ref.push()
            new_log_ref.set({
                'source': source,
                'message': message,
                'timestamp': int(time.time() * 1000)
            })
            # keep only latest 50 logs maybe? (For now just push, the UI can slice)
        except Exception as e:
            pass

    def listen_for_commands(self, callback):
        if not self.enabled:
            return
        
        print("🌐 Cloud Listener: Active (Waiting for dashboard commands...)")
        self.last_timestamp = int(time.time() * 1000) # Bỏ qua các lệnh cũ trước khi start

        def listener(event):
            if event.data:
                cmd = event.data
                # Chỉ xử lý lệnh mới sau khi hệ thống start
                if cmd.get('timestamp', 0) > self.last_timestamp:
                    self.last_timestamp = cmd.get('timestamp')
                    callback(cmd.get('text', ''), cmd.get('context', ''))

        db.reference('commands/last_command').listen(listener)

    def request_approval(self, approval_type, task_name, content):
        """Block until user approves or rejects via Dashboard UI."""
        if not self.enabled:
            print("⚠️ Skipping human-in-the-loop (Firebase disabled).")
            return "approved", ""
        
        if os.getenv("AUTO_APPROVE", "false").lower() == "true":
            print(f"⏩ [AUTO_APPROVE] Tự động duyệt {approval_type}: {task_name}")
            return "approved", ""
        try:
            ref = db.reference('approvals/current')
            ref.set({
                'type': approval_type,
                'task_name': task_name,
                'content': content,
                'status': 'pending',
                'feedback': ''
            })
            print(f"⏳ Đang chờ người dùng duyệt [{approval_type}] trên Dashboard...")
            
            while True:
                data = ref.get()
                if not data:
                    time.sleep(3)
                    continue
                    
                status = data.get('status')
                if status == 'approved':
                    ref.delete()
                    return "approved", ""
                elif status == 'rejected':
                    feedback = data.get('feedback', '')
                    ref.delete()
                    return "rejected", feedback
                    
                time.sleep(3)
        except Exception as e:
            print(f"❌ Approval Request Failed: {e}")
            return "approved", ""

# Script to helper user setup
if __name__ == "__main__":
    print("Firebase Sync Module Ready.")
