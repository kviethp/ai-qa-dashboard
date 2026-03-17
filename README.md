# 🚀 Hệ Thống Tự Động Hóa QA AI Thông Minh (Multi-Agent System)

Hệ thống **AI QA Automation** được thiết kế nguyên khối cho Team QA, tích hợp Multi-Agent (Nhiều AI cùng làm việc), quy trình duyệt Human-in-the-Loop, nhận thức ngữ cảnh sâu sắc (Context-Awareness), và giám sát theo thời gian thực (Real-time).

---

## 🌟 TÍNH NĂNG CỐT LÕI MỚI NHẤT

### 1. 👥 Multi-Agent Architecture (Đa Đặc Vụ)
Hệ thống chia việc thành các chuyên gia, quy trình phối hợp tự động nối đuôi nhau:
- **Ngài Thư ký / PM Agent**: Tiếp nhận lệnh điều phối tổng quan.
- **BA Agent (Business Analyst)**: Đọc Tài liệu Đặc tả (SRS), kịch bản (User Story, AC) để xuất ra Requirement chuẩn xác trước khi test.
- **Lead QA Agent**: Thiết kế Test Plan (Lập Kế Hoạch Test) theo Requirement đã chốt.
- **Playwright Coder Agent**: Viết Automation Code bằng ngôn ngữ Playwright/TypeScript dựa vào Plan trên.
- **Code Reviewer Agent**: Đóng vai Giám đốc kỹ thuật, check lỗi Code.

### 2. 🛡️ Human-in-the-Loop (Quy trình Duyệt của Con người)
AI không tự ý chạy toàn bộ quy trình. Hệ thống sẽ **TẠM DỪNG (Pauses)** và báo lên **Dashboard** chờ anh Việt duyệt ở 3 chốt chặn:
1.  **Duyệt Requirement**: (BA Agent -> Anh Việt) "Anh xem em hiểu logic tài liệu này thế này đã đúng chưa?"
2.  **Duyệt Test Plan**: (Lead QA -> Anh Việt) "Kịch bản em định test đây, anh duyệt để em bảo tụi nó Code nhé?"
3.  **Duyệt Code (Explainable AI)**: 
    *   Coder hiển thị chi tiết: `Tóm tắt thay đổi`, `Nguyên nhân gốc rễ (Root Cause)`, `Lý do giải pháp này tối ưu`.
    *   Anh Việt xem, gật đầu (Approve) thì code mới được ghi vào máy và chạy thử. Nếu sai, anh nhập Feedback bắt Coder sửa lại.

### 3. 🧠 Context-Awareness (Siêu Nhận Thức Ngữ Cảnh)
AI không còn "Mù mờ" làm mò mẫm nữa, nó được trang bị 3 tầng bản đồ:
- **Repository Map (Bản đồ Code)**: AI tự quét thư mục `e2e/pages` (Gồm File, Class, Tên Hàm) để ưu tiên tận dụng Code cũ (Reuse Code).
- **Business Context (Sổ tay Nghiệp Vụ)**: Upload tài liệu vào cột Context, hoặc lưu file Markdown vào `docs/business_flows/`, AI sẽ hút toàn bộ logic Business để test đúng ý định.
- **X-Ray Selector**: AI xài Tool trích xuất trực tiếp cây DOM trang web để không bao giờ "Đoán mò" Locator.

### 4. 💽 Multi-modal Data Ingestion & MCP Integration
Khả năng tiêu hóa dữ liệu đa phương thức mạnh mẽ:
-   **Dashboard Input**: Cho phép copy/paste SRS, User Story, Acceptance Criteria (AC) thẳng vào Dashboard để BA Agent lọc.
-   **Jira MCP Server (`mcp-servers/jira_mcp_server.py`)**: Công cụ chuẩn Model Context Protocol kết nối API thẳng vào Jira lấy dữ liệu thay vì copy/paste thủ công. (Sử dụng với Cursor/IDE ngoài).

### 5. ⚡ Tính Bền Bỉ, Ổn Định Chống Crash
-   **State Persistence (`state.json`)**: Hệ thống ghi nhớ nó đang làm đến bước nào (Đang chờ User duyệt Plan, hay đang viết Code dở). Nếu tắt đi bật lại, nó sẽ tiếp tục từ chỗ dang dở mà không mất trí nhớ hay chạy lại từ đầu.
-   **Auto-Retry**: Cơ chế tự động thử lại 3-5 lần nếu Coder viết sai Syntax.

### 6. 📱 Dashboard Hiện Đại & Chuyên Nghiệp (Mobile-Responsive)
-   Hiển thị **Real-time Status** thanh tiến trình từng Agent, trạng thái `Idle > Working > Waiting`.
-   **Live Terminal (Log thời gian thực)**: Mọi thao tác, tư duy log hệ thống được truyền trực tuyến từ Python (Backend) lên React (Frontend) qua Firebase siêu mượt.
-   Thiết kế giao diện 100% tương thích cả màn rộng lẫn di động, máy chủ nhỏ gọn.

---

## ⚙️ HƯỚNG DẪN CÀI ĐẶT & SỬ DỤNG HỆ THỐNG

### I. Khởi chạy Hệ Thống (Mở 2 Terminal)

#### 1. Khởi chạy Máy Chủ Điểu Phối (Python Backend)
Mở Terminal 1 vào thư mục `c:\Users\vietkq\.gemini\antigravity\playground\inner-rocket`:
```bash
# Set biến môi trường trỏ vào Local Ollama để AI hoạt động
$env:OLLAMA_HOST="http://localhost:11434"

# Chạy hệ thống lõi
python orchestrator.py
```
> Lúc này Backend sẽ hiển thị "Chờ lệnh từ Dashboard..."

#### 2. Khởi chạy Bảng Điều Khiển (React Frontend)
Mở Terminal 2 vào thư mục `inner-rocket/dashboard`:
```bash
npm run dev
```
> Trình duyệt sẽ mở cổng `http://localhost:5173`. Giao diện QA Center sẵn sàng!

### II. Cách Thao Tác Qua Dashboard

**Cách 1: Quick Task (Giao Việc Nhanh)**
-   Tại ô **"Nhập yêu cầu cho Sofia..."**: Nhập "Tạo test case cho tính năng Đăng Nhập Trang Chủ".
-   Bấm **"Gửi AI Team"**.
-   Agent sẽ nhảy vào làm, Lead QA sẽ sớm vẫy gọi chờ anh Duyệt Test Plan.

**Cách 2: Data Ingestion (Nhồi Tài Liệu BA)**
-   Nếu anh có bảng mô tả Ticket Jira, copy toàn bộ nội dung AC (Acceptance Criteria) đó.
-   Dán nội dung vào ô Textarea: **"Dán User Story, Acceptance Criteria, SRS..."** bên dưới thanh tìm kiếm.
-   Bấm gửi. BA Agent sẽ nhảy ra chặn đứng luồng làm việc, chuyển đổi tài liệu đó thành Scenario, ép anh duyệt Requirement một lần, sau đó QA mới vào cuộc.

**Cách 3: Approve & Reject (Duyệt Hoặc Mắng AI)**
-   Khi màn hình bật sáng popup **"Chờ Phê Duyệt"** (Ví dụ duyệt Code):
-   🟢 Nếu ưng ý: Bấm **Xong, Duyệt Luôn!**. Code sẽ ghi và Playwright tự động Test.
-   🔴 Nếu thấy ngu/Hoặc phát sinh lỗi: Ở ô text kế bên, nhập lý do (VD: *"Này, nút đăng ký em dùng sai xpath rồi, id của nó là #btn-regsiter"*), rồi bấm nút Đỏ **Yêu Cầu Sửa Lại**. AI Coder sẽ xin lỗi và chui về hầm ngầm viết lại Code đưa anh duyệt đến khi đúng thì thôi!

---

## 🛠️ NÂNG CAO: TÍCH HỢP JIRA MCP SERVER (CHO CURSOR)

Anh có thể sử dụng `jira_mcp_server.py` đã được tạo sẵn để kết nối hệ sinh thái MCP.

1.  Cài đặt thư viện: `pip install mcp requests`
2.  Cách thiết lập trong IDE/Orchestrator:
    - Set các biến môi trường:
      - `JIRA_BASE_URL` (Ví dụ: `https://tencongty.atlassian.net`)
      - `JIRA_EMAIL` (Email tài khoản Jira)
      - `JIRA_API_TOKEN` (Mã token cá nhân)
    - Chạy server: `python jira_mcp_server.py`

*(Tài liệu này đóng vai trò như Sổ Tay Trung Tâm cho Toàn bộ Team AI Automation System).*
