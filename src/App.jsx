import React, { useEffect, useState } from 'react';
import './App.css';
import { database, ref, onValue, isConfigured } from './firebase';

const Dashboard = () => {
  const [stats] = useState({
    successRate: 85,
    totalBugs: 12,
    memoryCount: 45,
    lastScan: "10:30 AM Today"
  });

  const [agentStatuses, setAgentStatuses] = useState({
    ba_agent: { name: "BA Đọc Lệnh", role: "Business Analyst", status: "idle", message: "Sẵn sàng" },
    lead_qa: { name: "Lead QA Việt", role: "Team Lead", status: "idle", message: "Sẵn sàng" },
    automation: { name: "Auto Bot", role: "Auto Engineer", status: "idle", message: "Sẵn sàng" },
    reviewer: { name: "Review Master", role: "Code Reviewer", status: "idle", message: "Sẵn sàng" },
    secretary: { name: "Thư ký Em", role: "Assistant", status: "idle", message: "Sẵn sàng" }
  });

  const [liveLogs, setLiveLogs] = useState([]);
  const [currentApproval, setCurrentApproval] = useState(null);
  const [approvalFeedback, setApprovalFeedback] = useState("");

  useEffect(() => {
    if (isConfigured) {
      console.log("☁️ Connecting to Firebase Realtime Database...");
      const statusRef = ref(database, 'agent_status');
      const unsubStatus = onValue(statusRef, (snapshot) => {
        const data = snapshot.val();
        if (data) {
          setAgentStatuses(prev => {
            const newState = { ...prev };
            Object.keys(data).forEach(id => {
              if (newState[id]) newState[id] = { ...newState[id], ...data[id] };
            });
            return newState;
          });
        }
      });
      
      const logsRef = ref(database, 'live_logs');
      const unsubLogs = onValue(logsRef, (snapshot) => {
        const data = snapshot.val();
        if (data) {
          const logsArray = Object.values(data).sort((a, b) => a.timestamp - b.timestamp);
          setLiveLogs(logsArray.slice(-100)); // Keep last 100 logs
        }
      });

      const approvalRef = ref(database, 'approvals/current');
      const unsubApproval = onValue(approvalRef, (snapshot) => {
        setCurrentApproval(snapshot.val() || null);
      });

      return () => {
        unsubStatus();
        unsubLogs();
        unsubApproval();
      };
    } else {
      console.log("🏠 Running in Local Mode (Fetching ./agent_status.json)");
      const fetchStatus = async () => {
        try {
          const response = await fetch('/agent_status.json');
          if (response.ok) {
            const data = await response.json();
            setAgentStatuses(prev => {
              const newState = { ...prev };
              Object.keys(data).forEach(id => {
                if (newState[id]) newState[id] = { ...newState[id], ...data[id] };
              });
              return newState;
            });
          }
        } catch (err) {
          console.error("Failed to fetch agent status", err);
        }
      };
      fetchStatus();
      const interval = setInterval(fetchStatus, 5000);
      return () => clearInterval(interval);
    }
  }, []);

  const [taskInput, setTaskInput] = useState("");
  const [contextInput, setContextInput] = useState(""); // State cho tài liệu SRS/AC
  const [isSending, setIsSending] = useState(false);
  const fileInputRef = React.useRef(null);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    try {
      if (file.name.endsWith('.docx')) {
        const arrayBuffer = await file.arrayBuffer();
        const mammoth = await import("mammoth/mammoth.browser.js").catch(() => import("mammoth"));
        const result = await mammoth.extractRawText({ arrayBuffer });
        setContextInput(prev => prev + (prev ? "\n\n" : "") + `--- NỘI DUNG TỪ DOCUMENT: ${file.name} ---\n` + result.value);
      } else {
        const reader = new FileReader();
        reader.onload = (event) => {
          const text = event.target.result;
          setContextInput(prev => prev + (prev ? "\n\n" : "") + `--- NỘI DUNG TỪ FILE: ${file.name} ---\n` + text);
        };
        reader.readAsText(file);
      }
    } catch (err) {
      console.error("Lỗi đọc file:", err);
      alert("⚠️ Không thể đọc file này. Vui lòng thử lại!");
    }
    // Reset file input
    e.target.value = '';
  };

  const recentBugs = [
    { id: 1, title: "Login form validation error", source: "GitLab", status: "Open", severity: "High" },
    { id: 2, title: "CSS alignment on Mobile view", source: "Jira", status: "In Progress", severity: "Medium" },
    { id: 3, title: "API Timeout on search", source: "GitLab", status: "Resolved", severity: "Critical" },
  ];

  const pushCommand = async () => {
    if (!taskInput.trim() || !isConfigured) return;
    setIsSending(true);
    try {
      const { set } = await import("firebase/database");
      const commandRef = ref(database, 'commands/last_command');
      await set(commandRef, {
        text: taskInput,
        context: contextInput, // Gửi Document Text
        timestamp: Date.now(),
        source: "dashboard"
      });
      setTaskInput("");
      setContextInput("");
      alert("🚀 Đã gửi yêu cầu tới AI Team!");
    } catch (err) {
      console.error("Failed to send command", err);
      alert("❌ Lỗi khi gửi lệnh.");
    } finally {
      setIsSending(false);
    }
  };

  const handleApprove = async () => {
    const { update } = await import("firebase/database");
    await update(ref(database, 'approvals/current'), { status: 'approved' });
  };

  const handleReject = async () => {
    if (!approvalFeedback.trim()) return alert("⚠️ Vui lòng nhập lý do (feedback) nếu bạn từ chối hoặc yêu cầu sửa đổi!");
    const { update } = await import("firebase/database");
    await update(ref(database, 'approvals/current'), { 
      status: 'rejected', 
      feedback: approvalFeedback 
    });
    setApprovalFeedback("");
  };

  return (
    <div className="dashboard-container">
      <header className="glass">
        <div className="header-main">
          <h1>🚀 AI QA Command Center</h1>
          <div className="user-info">Welcome, <span>Anh Việt</span></div>
        </div>
      </header>

      <main>
        {/* New Command Section */}
        <section className="command-section glass">
          <h2>🎯 Giao việc từ xa & Cung cấp Tài liệu (Remote Control)</h2>
          <div className="command-box">
            <div className="input-group">
              <input 
                type="text" 
                placeholder="Nhập yêu cầu cho Sofia... (ví dụ: Hãy test lại tính năng đăng nhập)" 
                value={taskInput}
                onChange={(e) => setTaskInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && pushCommand()}
                className="main-input"
              />
              <textarea
                placeholder="Dán User Story, link Figma/Jira, hoặc Upload File SRS (txt, md) vào đây để BA Agent phân tích..."
                value={contextInput}
                onChange={(e) => setContextInput(e.target.value)}
                className="context-input"
                rows="3"
              />
              <div className="upload-controls">
                <input 
                  type="file" 
                  ref={fileInputRef} 
                  style={{ display: 'none' }} 
                  onChange={handleFileUpload} 
                  accept=".txt,.md,.json,.csv,.docx"
                />
                <button 
                  onClick={() => fileInputRef.current && fileInputRef.current.click()} 
                  className="btn-upload"
                >
                  📎 Đính kèm File (TXT/MD/DOCX)
                </button>
              </div>
            </div>
            <button className="btn-send-main" onClick={pushCommand} disabled={isSending || !taskInput.trim()}>
              {isSending ? "Đang gửi..." : "🚀 Gửi Yêu Cầu"}
            </button>
          </div>
          <p className="hint">Mẹo: Thêm tài liệu tham khảo (Nghiệp vụ) giúp AI chuẩn xác 100% không bị ảo giác.</p>
        </section>

        {currentApproval && currentApproval.status === 'pending' && (
          <section className="approval-section glass alert-border">
            <h2>⚠️ Chờ Phê Duyệt: {currentApproval.task_name}</h2>
            <div className="badge type-approval">{currentApproval.type}</div>
            <div className="approval-content markdown-preview">
              <pre>{currentApproval.content}</pre>
            </div>
            <div className="approval-actions">
              <button onClick={handleApprove} className="btn-approve">✅ Ngon, Duyệt Luôn</button>
              <div className="reject-box">
                <input 
                  type="text" 
                  placeholder="Nhập feedback hướng dẫn AI sửa đổi lại..."
                  value={approvalFeedback}
                  onChange={e => setApprovalFeedback(e.target.value)}
                />
                <button onClick={handleReject} className="btn-reject">❌ Yêu Cầu Sửa Lại</button>
              </div>
            </div>
          </section>
        )}

        <section className="stats-grid">
          {/* ... existing stats ... */}
          <div className="card glass">
            <h3>Success Rate</h3>
            <div className="value success">{stats.successRate}%</div>
            <p>Overall project health</p>
          </div>
          <div className="card glass">
            <h3>Active Bugs</h3>
            <div className="value alert">{stats.totalBugs}</div>
            <p>Reported across GitLab/Jira</p>
          </div>
          <div className="card glass">
            <h3>AI Memory</h3>
            <div className="value info">{stats.memoryCount}</div>
            <p>Learned experiences</p>
          </div>
          <div className="card glass">
            <h3>Multi-tier Status</h3>
            <div className="value">Active</div>
            <p>Last scan: {stats.lastScan}</p>
          </div>
        </section>

        <section className="agent-status-section">
          <h2>🤖 AI Agent Status</h2>
          <div className="agent-grid">
            {Object.entries(agentStatuses).map(([id, agent]) => (
              <div key={id} className={`agent-card glass ${agent.status}`}>
                <div className="agent-info">
                  <div className="agent-header">
                    <span className="agent-name">{agent.name}</span>
                    <span className={`status-pill ${agent.status}`}>{agent.status.toUpperCase()}</span>
                  </div>
                  <div className="agent-role">{agent.role}</div>
                  <div className="agent-msg">"{agent.message}"</div>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="live-terminal-section glass">
          <h2>🖥️ Live Terminal (Real-time Logs)</h2>
          <div className="terminal-window">
             <div className="terminal-header">
               <span className="dot red"></span>
               <span className="dot yellow"></span>
               <span className="dot green"></span>
             </div>
             <div className="terminal-body" ref={el => { if (el) el.scrollTop = el.scrollHeight; }}>
                {liveLogs.length === 0 ? <div className="log-line empty">Chưa có log hệ thống...</div> : 
                 liveLogs.map((log, idx) => (
                   <div key={idx} className={`log-line type-${log.source}`}>
                     <span className="log-time">[{new Date(log.timestamp).toLocaleTimeString()}]</span>
                     <span className="log-source">[{log.source.toUpperCase()}]</span>
                     <span className="log-msg">{log.message}</span>
                   </div>
                 ))
                }
             </div>
          </div>
        </section>

        <div className="responsive-row">
          <section className="reports-section glass">
            <h2>Recent Bug Reports</h2>
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Title</th>
                    <th>Platform</th>
                    <th>Severity</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {recentBugs.map(bug => (
                    <tr key={bug.id}>
                      <td>{bug.title}</td>
                      <td><span className="badge">{bug.source}</span></td>
                      <td><span className={`severity ${bug.severity.toLowerCase()}`}>{bug.severity}</span></td>
                      <td>{bug.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="memory-section glass">
            <h2>🧠 AI Neural Memory</h2>
            <div className="memory-item">
              <strong>Optimized Login Flow</strong>: AI automatically applied POM.
            </div>
            <div className="memory-item">
              <strong>Selector Auto-healing</strong>: Fixed 3 broken locators.
            </div>
          </section>
        </div>

      </main>

      <footer>
        Made with ❤️ by Secretary Em for <span>Anh Việt</span>
      </footer>
    </div>
  );
};

export default Dashboard;
