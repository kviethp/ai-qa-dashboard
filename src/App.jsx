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
    lead_qa: { name: "Lead QA Việt", role: "Team Lead", status: "idle", message: "Sẵn sàng" },
    automation: { name: "Auto Bot", role: "Auto Engineer", status: "idle", message: "Sẵn sàng" },
    reviewer: { name: "Review Master", role: "Code Reviewer", status: "idle", message: "Sẵn sàng" },
    secretary: { name: "Thư ký Em", role: "Assistant", status: "idle", message: "Sẵn sàng" }
  });

  useEffect(() => {
    if (isConfigured) {
      console.log("☁️ Connecting to Firebase Realtime Database...");
      const statusRef = ref(database, 'agent_status');
      return onValue(statusRef, (snapshot) => {
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
  const [isSending, setIsSending] = useState(false);

  const recentBugs = [
    { id: 1, title: "Login form validation error", source: "GitLab", status: "Open", severity: "High" },
    { id: 2, title: "CSS alignment on Mobile view", source: "Jira", status: "In Progress", severity: "Medium" },
    { id: 3, title: "API Timeout on search", source: "GitLab", status: "Resolved", severity: "Critical" },
  ];

  const pushCommand = async () => {
    if (!taskInput.trim() || !isConfigured) return;
    setIsSending(true);
    try {
      // Chúng ta sẽ push vào 'commands' với timestamp để Sofia nhận diện mới nhất
      const { set } = await import("firebase/database");
      const commandRef = ref(database, 'commands/last_command');
      await set(commandRef, {
        text: taskInput,
        timestamp: Date.now(),
        source: "dashboard"
      });
      setTaskInput("");
      alert("🚀 Đã gửi yêu cầu tới Sofia!");
    } catch (err) {
      console.error("Failed to send command", err);
      alert("❌ Lỗi khi gửi lệnh.");
    } finally {
      setIsSending(false);
    }
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
          <h2>🎯 Giao việc từ xa (Remote Control)</h2>
          <div className="command-box">
            <input 
              type="text" 
              placeholder="Nhập yêu cầu cho Sofia... (ví dụ: Hãy test lại tính năng đăng nhập)" 
              value={taskInput}
              onChange={(e) => setTaskInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && pushCommand()}
            />
            <button onClick={pushCommand} disabled={isSending || !taskInput.trim()}>
              {isSending ? "Đang gửi..." : "Gửi Sofia"}
            </button>
          </div>
          <p className="hint">Mẹo: Sofia sẽ nhận lệnh và báo cáo qua Telegram cho Anh.</p>
        </section>

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
