import React, { useEffect, useState, useRef } from 'react';
import './App.css';
import { database, ref, onValue, set, isConfigured } from './firebase';
import { 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip 
} from 'recharts';
import { Activity, Cpu, Database, Clipboard, Layout, FileText, Send, MessageSquare, Check, X, Maximize2 } from 'lucide-react';

const Dashboard = () => {
  const [stats] = useState({
    successRate: 85,
    totalBugs: 12,
    memoryCount: 45,
    lastScan: "10:30 AM Today"
  });

  const [agentStatuses, setAgentStatuses] = useState({
    ba_agent: { name: "Business Analyser", role: "BA Agent", status: "idle", message: "Sẵn sàng" },
    lead_qa: { name: "QA Lead", role: "Lead Agent", status: "idle", message: "Sẵn sàng" },
    automation: { name: "Automation Tester", role: "Auto Engineer", status: "idle", message: "Sẵn sàng" },
    reviewer: { name: "Reviewer", role: "Review Agent", status: "idle", message: "Sẵn sàng" },
    secretary: { name: "Sofia", role: "Special Secretary", status: "idle", message: "Sẵn sàng" }
  });

  const [liveLogs, setLiveLogs] = useState([]);
  const [currentApproval, setCurrentApproval] = useState(null);
  const [approvalFeedback, setApprovalFeedback] = useState("");
  const [activeTab, setActiveTab] = useState("all");
  const [dragActive, setDragActive] = useState(false);
  const [healthData, setHealthData] = useState([]);
  const [agentChatInput, setAgentChatInput] = useState("");
  const [isFullContext, setIsFullContext] = useState(false);

  // Width detection for charts
  const [containerWidth, setContainerWidth] = useState(0);
  const chartWrapperRef = useRef(null);

  useEffect(() => {
    const updateWidth = () => {
      if (chartWrapperRef.current) {
        setContainerWidth(chartWrapperRef.current.offsetWidth);
      }
    };
    updateWidth();
    const observer = new ResizeObserver(updateWidth);
    if (chartWrapperRef.current) observer.observe(chartWrapperRef.current);
    return () => observer.disconnect();
  }, []);


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
          const newLogs = logsArray.slice(-100);
          setLiveLogs(newLogs);
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
  const [contextInput, setContextInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const fileInputRef = React.useRef(null);

  // Health Data Simulator (or can be connected to real stats)
  useEffect(() => {
    const interval = setInterval(() => {
      setHealthData(prev => {
        const newData = [...prev, {
          time: new Date().toLocaleTimeString().slice(-8),
          latency: Math.floor(Math.random() * 200) + 100,
          tokens: Math.floor(Math.random() * 500) + 800
        }].slice(-15);
        return newData;
      });
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") setDragActive(true);
    else if (e.type === "dragleave") setDragActive(false);
  };

  const handleDrop = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      if (file.type.startsWith('image/')) {
        alert("🖼️ Phát hiện ảnh chụp màn hình! AI đang sử dụng Vision để phân tích giao diện...");
        // Mock Vision Analysis
        setTaskInput("Phân tích giao diện từ ảnh chụp màn hình và đề xuất Test Case...");
      }
      handleFileUpload({ target: { files: [file] } });
    }
  };

  const handleFileUpload = async (e) => {
    // ... logic remains same or similar ...
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
    }
  };

  const recentBugs = [
    { id: 1, title: "Login form validation error", source: "GitLab", status: "Open", severity: "High" },
    { id: 2, title: "CSS alignment on Mobile view", source: "Jira", status: "In Progress", severity: "Medium" },
    { id: 3, title: "API Timeout on search", source: "GitLab", status: "Resolved", severity: "Critical" },
  ];

  const pushCommand = (text = null, agent = null) => {
    if (!isConfigured) return;
    const commandText = text || taskInput;
    if (!commandText.trim()) return;

    setIsSending(true);
    const cmdRef = ref(database, 'commands/last_command');
    const newCmd = {
      text: commandText,
      context: contextInput,
      target_agent: agent || (activeTab !== 'all' && activeTab !== 'system' ? activeTab : null),
      timestamp: Date.now()
    };
    
    set(cmdRef, newCmd).then(() => {
      setIsSending(false);
      if (!agent) {
        setTaskInput("");
        setContextInput("");
        alert("🚀 Đã gửi yêu cầu tới AI Team!");
      } else {
        setAgentChatInput("");
      }
    }).catch((err) => {
      console.error("Failed to send command", err);
      alert("❌ Lỗi khi gửi lệnh.");
      setIsSending(false);
    });
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
        {/* System Health Monitor (Proposal 4) */}
        <section className="health-section glass">
          <div className="section-header">
            <h2><Activity size={20} /> System Health & Intelligence</h2>
            <div className="health-stats">
              <div className="stat-pill"><Cpu size={14} /> Latency: {healthData[healthData.length-1]?.latency}ms</div>
              <div className="stat-pill"><Database size={14} /> Tokens/s: {healthData[healthData.length-1]?.tokens}</div>
            </div>
          </div>
          <div className="chart-container" style={{ height: 180, width: '100%', marginTop: '1rem' }}>
            <ResponsiveContainer>
              <AreaChart data={healthData}>
                <defs>
                  <linearGradient id="colorLatency" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="time" hide />
                <YAxis hide />
                <Tooltip 
                  contentStyle={{ background: '#1e293b', border: 'none', borderRadius: '8px' }}
                  itemStyle={{ color: '#fff' }}
                />
                <Area type="monotone" dataKey="latency" stroke="#6366f1" fillOpacity={1} fill="url(#colorLatency)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </section>

        {currentApproval && currentApproval.status === 'pending' && (
          <section className="approval-section glass">
            <div className="section-header">
              <h2>⚠️ CHỜ PHÊ DUYỆT: {currentApproval.task_name}</h2>
              <div className="approval-badges">
                <span className="badge type-approval" style={{ background: '#7c3aed', color: 'white', padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 'bold' }}>{currentApproval.type}</span>
                <button 
                   className="btn-icon-mini" 
                   onClick={() => setIsFullContext(!isFullContext)}
                   title={isFullContext ? "Thu nhỏ" : "Xem đầy đủ"}
                >
                  <Maximize2 size={14} />
                </button>
              </div>
            </div>
            
            <div className={`approval-content markdown-preview ${isFullContext ? 'full' : 'compact'}`}>
              <pre>{currentApproval.content}</pre>
            </div>
            
            <div className="approval-actions-v2">
              <button onClick={handleApprove} className="btn-approve-v2">
                <Check size={18} /> ✅ DUYỆT NGAY
              </button>
              <div className="reject-group">
                <input 
                  type="text" 
                  placeholder="Yêu cầu sửa đổi (Feedback)..."
                  value={approvalFeedback}
                  onChange={e => setApprovalFeedback(e.target.value)}
                />
                <button onClick={handleReject} className="btn-reject-v2">
                  <X size={18} /> SỬA LẠI
                </button>
              </div>
            </div>
          </section>
        )}

        {/* New Command Section with Drag & Drop (Proposal 3) */}
        <section 
          className={`command-section glass ${dragActive ? 'drag-active' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <div className="section-header">
            <h2><Layout size={20} /> Giao việc & Requirement (BA Center)</h2>
            {dragActive && <div className="drag-overlay">🚀 Thả file vào đây để BA trích xuất Requirement!</div>}
          </div>
          <div className="command-box">
            <div className="input-group">
              <div className="input-with-icon">
                <Clipboard size={18} className="icon" />
                <input 
                  type="text" 
                  placeholder="Nhập yêu cầu cho Sofia... (ví dụ: Hãy test lại tính năng đăng nhập)" 
                  value={taskInput}
                  onChange={(e) => setTaskInput(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && pushCommand()}
                  className="main-input"
                />
              </div>
              <div className="input-with-icon">
                <FileText size={18} className="icon top" />
                <textarea
                  placeholder="Hất file SRS/Figma vào đây hoặc dán nội dung để BA phân tích..."
                  value={contextInput}
                  onChange={(e) => setContextInput(e.target.value)}
                  className="context-input"
                  rows="3"
                />
              </div>
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
                  📎 Đính kèm File (TX/MD/DOCX)
                </button>
                <button className="btn-send-main" onClick={pushCommand} disabled={isSending || !taskInput.trim()}>
                  {isSending ? <Activity size={18} className="animate-spin" /> : <>🚀 Gửi Yêu Cầu</>}
                </button>
              </div>
            </div>
          </div>
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

        <section className="live-terminal-section glass">
          <div className="section-header">
            <h2>🖥️ Live Terminal & Interaction</h2>
            <div className="terminal-tabs">
                <button className={`tab-btn ${activeTab === 'all' ? 'active' : ''}`} onClick={() => setActiveTab('all')}>Tất cả</button>
                <button className={`tab-btn ${activeTab === 'system' ? 'active' : ''}`} onClick={() => setActiveTab('system')}>Hệ thống</button>
                <button className={`tab-btn ${activeTab === 'secretary' ? 'active' : ''}`} onClick={() => setActiveTab('secretary')}>Thư ký Sofia</button>
                <button className={`tab-btn ${activeTab === 'ba_agent' ? 'active' : ''}`} onClick={() => setActiveTab('ba_agent')}>Business Analyser</button>
                <button className={`tab-btn ${activeTab === 'lead_qa' ? 'active' : ''}`} onClick={() => setActiveTab('lead_qa')}>QA Lead</button>
                <button className={`tab-btn ${activeTab === 'automation' ? 'active' : ''}`} onClick={() => setActiveTab('automation')}>Automation Tester</button>
                <button className={`tab-btn ${activeTab === 'reviewer' ? 'active' : ''}`} onClick={() => setActiveTab('reviewer')}>Reviewer</button>
             </div>
          </div>
          <div className="terminal-window">
             <div className="terminal-header">
               <span className="dot red"></span>
               <span className="dot yellow"></span>
               <span className="dot green"></span>
             </div>
             <div className="terminal-body" ref={el => { if (el) el.scrollTop = el.scrollHeight; }}>
                {liveLogs.filter(l => activeTab === 'all' || l.source === activeTab).length === 0 ? 
                 <div className="log-line empty">Chưa có log từ đặc vụ này...</div> : 
                 liveLogs
                  .filter(l => activeTab === 'all' || l.source === activeTab)
                  .map((log, idx) => (
                    <div key={idx} className={`log-line type-${log.source}`}>
                      <span className="log-time">[{new Date(log.timestamp).toLocaleTimeString()}]</span>
                      <span className="log-source">[{log.source.toUpperCase()}]</span>
                      <span className="log-msg">{log.message}</span>
                    </div>
                  ))
                }
             </div>
             {/* Permanent Chat Box for Interaction (Proposal 2) */}
             <div className="agent-chat-input">
                <div className="chat-container-inner">
                  <div className="agent-selector-mini">
                    <MessageSquare size={16} className="chat-icon" />
                    <select 
                      value={activeTab === 'all' || activeTab === 'system' ? 'secretary' : activeTab} 
                      onChange={(e) => setActiveTab(e.target.value)}
                    >
                      <option value="secretary">Sofia</option>
                      <option value="ba_agent">Business Analyser</option>
                      <option value="lead_qa">QA Lead</option>
                      <option value="automation">Tester</option>
                      <option value="reviewer">Reviewer</option>
                    </select>
                  </div>
                  <input 
                    type="text" 
                    placeholder={`Gửi tin nhắn riêng tới ${
                      activeTab === 'secretary' ? 'Thư ký Sofia' :
                      activeTab === 'ba_agent' ? 'Business Analyser' :
                      activeTab === 'lead_qa' ? 'QA Lead' :
                      activeTab === 'automation' ? 'Automation Tester' :
                      activeTab === 'reviewer' ? 'Reviewer' : 'Sofia'
                    }...`} 
                    value={agentChatInput}
                    onChange={(e) => setAgentChatInput(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && pushCommand(agentChatInput, (activeTab === 'all' || activeTab === 'system' ? 'secretary' : activeTab))}
                  />
                  <button onClick={() => pushCommand(agentChatInput, (activeTab === 'all' || activeTab === 'system' ? 'secretary' : activeTab))}>
                    <Send size={14} />
                  </button>
                </div>
                <p className="chat-hint">Sếp có thể nhắn tin trực tiếp để hướng dẫn từng Agent mà không cần chạy cả quy trình.</p>
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
        Made with ❤️ by Thư ký Sofia for <span>Anh Việt</span>
      </footer>
    </div>
  );
};

export default Dashboard;
