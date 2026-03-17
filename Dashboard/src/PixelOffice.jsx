import React, { useEffect, useState, useRef } from 'react';
import './PixelOffice.css';
import agentSprites from './assets/agent_sprites.png';
import agentWalking from './assets/agent_walking.png';
import officeMap from './assets/office_map.png';

const PixelOffice = () => {
  const [agentStatuses, setAgentStatuses] = useState({
    lead_qa: { status: 'idle', message: 'Ready', task: 'Monitoring', model: 'Qwen-14B' },
    automation: { status: 'idle', message: 'Coffee', task: 'Idle', model: 'Qwen-14B' },
    reviewer: { status: 'idle', message: 'Resting', task: 'Idle', model: 'Qwen-14B' },
    secretary: { status: 'working', message: 'Planning', task: 'Scheduling', model: 'Qwen-14B' }
  });

  const [selectedAgent, setSelectedAgent] = useState(null);
  const [movingAgents, setMovingAgents] = useState({});
  const prevPositions = useRef({});

  const zones = {
    work: [
      { x: 14.5, y: 175 }, // Desk 1 Right
      { x: 26.5, y: 175 }, // Desk 2 Right
      { x: 14.5, y: 330 }, // Desk 3 Right
      { x: 26.5, y: 330 }  // Desk 4 Right
    ],
    pantry: [
      { x: 74, y: 90 },
      { x: 84, y: 90 }
    ],
    lounge: [
      { x: 72, y: 365 },
      { x: 86, y: 365 }
    ]
  };

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const response = await fetch('/agent_status.json');
        if (response.ok) {
          const data = await response.json();
          setAgentStatuses(prev => {
            const newState = { ...prev, ...data };
            // Simple movement detection
            Object.keys(newState).forEach(id => {
              const isWorking = newState[id].status === 'working';
              const targetZone = isWorking ? 'work' : 'pantry'; // Simplified
              if (prevPositions.current[id] !== targetZone) {
                setMovingAgents(m => ({ ...m, [id]: true }));
                setTimeout(() => setMovingAgents(m => ({ ...m, [id]: false })), 1500);
                prevPositions.current[id] = targetZone;
              }
            });
            return newState;
          });
        }
      } catch (e) {}
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  const agents = [
    { id: 'lead_qa', name: 'Lead QA Việt', charIdx: 0, idleZone: 'pantry', idleIdx: 0, role: 'Team Lead' },
    { id: 'automation', name: 'Auto Bot', charIdx: 1, idleZone: 'lounge', idleIdx: 0, role: 'Auto Engineer' },
    { id: 'reviewer', name: 'Review Master', charIdx: 2, idleZone: 'pantry', idleIdx: 1, role: 'Code Reviewer' },
    { id: 'secretary', name: 'Thư ký Em', charIdx: 3, idleZone: 'lounge', idleIdx: 1, role: 'Assistant' },
  ];

  return (
    <div className="office-sim-v4">
      <div className="sim-header">
        <div className="led-status">🔴 LIVE AI OPERATIONS</div>
        <h3>Office Simulation v3.2</h3>
      </div>

      <div className="sim-viewport" style={{ backgroundImage: `url(${officeMap})` }}>
        {agents.map((agent, index) => {
          const status = agentStatuses[agent.id] || { status: 'idle', message: '...' };
          const isWorking = status.status === 'working';
          const isWalking = movingAgents[agent.id];
          
          let pos;
          if (isWorking) {
            pos = zones.work[index];
          } else {
            pos = agent.idleZone === 'pantry' ? zones.pantry[agent.idleIdx] : zones.lounge[agent.idleIdx];
          }

          const isSelected = selectedAgent === agent.id;

          return (
            <div 
              key={agent.id}
              className={`sim-entity ${isWalking ? 'walking' : ''} ${isSelected ? 'active-inspect' : ''}`}
              style={{ left: `${pos.x}%`, top: `${pos.y}px` }}
              onClick={() => setSelectedAgent(isSelected ? null : agent.id)}
            >
              <div className={`sim-bubble ${isWorking ? 'visible' : ''}`}>
                {status.message}
              </div>

              <div 
                className={`sim-sprite char-${agent.charIdx} ${isWorking ? 'working' : (isWalking ? 'walk' : 'idle')}`}
                style={{ 
                  backgroundImage: `url(${isWalking ? agentWalking : agentSprites})`
                }}
              ></div>

              <div className="sim-name-tag">
                <span className="sim-status-dot"></span> {agent.name}
              </div>

              {isSelected && (
                <div className="sim-inspector-mini">
                  <div className="ins-header">{agent.name} <span className="ins-close">×</span></div>
                  <div className="ins-body">
                    <p><span>Task:</span> {status.task || 'Waiting'}</p>
                    <p><span>Brain:</span> {status.model || 'Qwen-14B'}</p>
                    <p><span>Mode:</span> {status.status.toUpperCase()}</p>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
      
      <div className="sim-legend">
        Click agent to inspect. Agents sit/type when WORKING and walk during transitions.
      </div>
    </div>
  );
};

export default PixelOffice;
