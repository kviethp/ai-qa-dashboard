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

  const recentBugs = [
    { id: 1, title: "Login form validation error", source: "GitLab", status: "Open", severity: "High" },
    { id: 2, title: "CSS alignment on Mobile view", source: "Jira", status: "In Progress", severity: "Medium" },
    { id: 3, title: "API Timeout on search", source: "GitLab", status: "Resolved", severity: "Critical" },
  ];

  return (
    <div className="dashboard-container">
      <header className="glass">
        <h1>🚀 AI QA Command Center</h1>
        <div className="user-info">Welcome, <span>Anh Việt</span></div>
      </header>

      <main>
        <section className="stats-grid">
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

        <section className="reports-section glass">
          <h2>Recent Bug Reports</h2>
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
        </section>

        <section className="memory-section glass">
          <h2>🧠 AI Neural Memory (Vector DB)</h2>
          <div className="memory-item">
            <strong>Optimized Login Flow</strong>: AI automatically applied Page Object Model from past experience.
          </div>
          <div className="memory-item">
            <strong>Selector Auto-healing</strong>: Fixed 3 broken locators by comparing with previous DOM states.
          </div>
        </section>

      </main>

      <footer>
        Made with ❤️ by Secretary Em for <span>Anh Việt</span>
      </footer>
    </div>
  );
};

export default Dashboard;
