import React, { useState, useEffect, useRef } from 'react';
import { Send } from 'lucide-react';
import './App.css';

const API_HEADERS = {
    'X-Arthur-Client': 'Arthur-Prime-V1'
};

// Icons
const IconMenu = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="3" y1="12" x2="21" y2="12"></line>
    <line x1="3" y1="6" x2="21" y2="6"></line>
    <line x1="3" y1="18" x2="21" y2="18"></line>
  </svg>
);

const IconDashboard = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="3" width="7" height="7"></rect>
    <rect x="14" y="3" width="7" height="7"></rect>
    <rect x="14" y="14" width="7" height="7"></rect>
    <rect x="3" y="14" width="7" height="7"></rect>
  </svg>
);

const IconHistory = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="10"></circle>
    <polyline points="12 6 12 12 16 14"></polyline>
  </svg>
);

const IconAgents = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
    <circle cx="9" cy="7" r="4"></circle>
    <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
    <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
  </svg>
);

const IconSettings = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="3"></circle>
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
  </svg>
);

const IconCat = () => (
    <svg width="40" height="40" viewBox="0 0 24 24" fill="black" stroke="none">
        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-5-9h2v2H7v-2zm8 0h2v2h-2v-2zm-4 4h4v2h-4v-2z"/>
    </svg>
);


function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [view, setView] = useState<'login' | 'register' | 'dashboard' | 'history' | 'agents' | 'settings'>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Agents State
  const [agents, setAgents] = useState<Array<{id: number, name: string, prompt: string, created_at?: string}>>([]);
  const [newAgentName, setNewAgentName] = useState('');
  const [newAgentPrompt, setNewAgentPrompt] = useState('');
  const [isCreatingAgent, setIsCreatingAgent] = useState(false);
  const [isSessionExpired, setIsSessionExpired] = useState(false);

  const authenticatedFetch = async (url: string, options: RequestInit = {}) => {
      const headers = {
          'Authorization': `Bearer ${token}`,
          ...API_HEADERS,
          ...((options.headers as Record<string, string>) || {})
      };
      
      const res = await fetch(url, { ...options, headers });
      if (res.status === 401) {
          setIsSessionExpired(true);
      }
      return res;
  };

  const handleNavigation = (newView: typeof view) => {
      if (isSessionExpired) {
          handleLogout();
          return;
      }
      setView(newView);
      setIsSidebarOpen(false);
  };

  // Check valid token on load (optional: verify with backend)
  useEffect(() => {
    if (token) {
        setView('dashboard');
        authenticatedFetch('/users/me')
        .then(res => {
            if (res.ok) return res.json();
            // If token is invalid, we might want to logout, but for now just log error
            throw new Error('Failed to fetch user info');
        })
        .then(data => {
            setUsername(data.username);
        })
        .catch(console.error);
    }
  }, [token]);

  const [chatInput, setChatInput] = useState('');
  const [chatHistory, setChatHistory] = useState<Array<{role: string, content: string}>>([]);
  const [fullHistory, setFullHistory] = useState<Array<any>>([]);
  const [selectedSessions, setSelectedSessions] = useState<number[]>([]);
  const [nukeProgress, setNukeProgress] = useState(0);
  const nukeTimerRef = useRef<number | null>(null);

  useEffect(() => {
    if (view === 'history' && token) {
        fetchHistory();
    }
    if (view === 'agents' && token) {
        fetchAgents();
    }
  }, [view, token]);

  const fetchAgents = () => {
    // The router prefix is /api/agents
    authenticatedFetch('/api/agents/')
    .then(res => res.json())
    .then(data => setAgents(data))
    .catch(console.error);
  };

  const handleCreateAgent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newAgentName.trim() || !newAgentPrompt.trim()) return;

    try {
        const res = await authenticatedFetch('/api/agents/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name: newAgentName, prompt: newAgentPrompt })
        });
        if (res.ok) {
            setNewAgentName('');
            setNewAgentPrompt('');
            setIsCreatingAgent(false);
            fetchAgents();
        }
    } catch (e) {
        console.error(e);
    }
  };

  const handleDeleteAgent = async (id: number) => {
      if(!confirm("Delete this agent?")) return;
      try {
          const res = await authenticatedFetch(`/api/agents/${id}`, {
              method: 'DELETE',
          });
          if (res.ok) fetchAgents();
      } catch (e) {
          console.error(e);
      }
  };

  const fetchHistory = () => {
      authenticatedFetch('/api/chat/history')
        .then(res => res.json())
        .then(data => {
            setFullHistory(data);
            setSelectedSessions([]);
        })
        .catch(console.error);
  }

  const toggleSession = (id: number) => {
      setSelectedSessions(prev => 
        prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]
      );
  };

  const handleDeleteSelected = async () => {
      if (selectedSessions.length === 0) return;
      if (!confirm(`Delete ${selectedSessions.length} sessions?`)) return;

      try {
          const res = await authenticatedFetch('/api/chat/sessions', {
              method: 'DELETE',
              headers: {
                  'Content-Type': 'application/json',
              },
              body: JSON.stringify({ session_ids: selectedSessions })
          });
          if (res.ok) {
              fetchHistory();
          }
      } catch (e) {
          console.error(e);
      }
  };

  const startNuke = () => {
    let progress = 0;
    if (nukeTimerRef.current) clearInterval(nukeTimerRef.current);
    
    nukeTimerRef.current = window.setInterval(() => {
        progress += 4; // 25 steps * 40ms = 1000ms
        setNukeProgress(progress);
        if (progress >= 100) {
            if(nukeTimerRef.current) clearInterval(nukeTimerRef.current);
            handleNukeHistory();
            setNukeProgress(0);
        }
    }, 40);
  };

  const cancelNuke = () => {
      if (nukeTimerRef.current) {
          clearInterval(nukeTimerRef.current);
          nukeTimerRef.current = null;
      }
      setNukeProgress(0);
  };

  const handleNukeHistory = async () => {
      try {
          const res = await authenticatedFetch('/api/chat/history', {
              method: 'DELETE',
          });
          if (res.ok) {
              alert("HISTORY NUKED");
              fetchHistory();
          }
      } catch (e) {
          console.error(e);
      }
  };

  const handleChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;
    
    const userMessage = { role: 'user', content: chatInput };
    setChatHistory(prev => [...prev, userMessage]);
    setChatInput('');

    try {
        const res = await authenticatedFetch('/api/chat', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text: userMessage.content }),
        });
        
        if (res.ok) {
            // Ideally we'd get a response back. For now just acknowledgment or updated history.
        } else {
            console.error("Failed to send chat message");
        }
    } catch (err) {
        console.error(err);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    try {
      const res = await fetch('/token', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/x-www-form-urlencoded',
            ...API_HEADERS
        },
        body: formData,
      });
      if (!res.ok) throw new Error('Login failed');
      const data = await res.json();
      localStorage.setItem('token', data.access_token);
      setToken(data.access_token);
      setView('dashboard');
      setError('');
    } catch (err) {
      setError('Invalid credentials');
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await fetch('/register', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            ...API_HEADERS
        },
        body: JSON.stringify({ username, password }),
      });
      if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || 'Registration failed');
      }
      alert('Account created! Please login.');
      setView('login');
      setError('');
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setView('login');
    setUsername('');
    setPassword('');
    setIsSessionExpired(false);
  };
  
  const handleDeleteAccount = async () => {
      if(!confirm("Are you sure? This cannot be undone.")) return;
      try {
          const res = await authenticatedFetch('/users/me', {
              method: 'DELETE',
          });
          if(res.ok) handleLogout();
          else alert("Failed to delete");
      } catch(e) {
          alert("Error deleting account");
      }
  }

  if (['dashboard', 'history', 'agents', 'settings'].includes(view)) {
    return (
      <div className="app-layout">
        <header className="mobile-header">
            <button className="menu-btn" onClick={() => setIsSidebarOpen(true)}>
                <IconMenu />
            </button>
            <span className="mobile-brand">Arthur Prime</span>
        </header>
        
        {isSidebarOpen && <div className="sidebar-overlay" onClick={() => setIsSidebarOpen(false)} />}

        <aside className={`sidebar ${isSidebarOpen ? 'open' : ''}`}>
            <div className="sidebar-header">
                <IconCat />
                <div className="brand-text">
                    <strong>Arthur Prime</strong><br/>
                </div>
            </div>

            <nav className="sidebar-nav">
                <button 
                    className={`nav-item ${view === 'dashboard' ? 'active' : ''}`}
                    onClick={() => handleNavigation('dashboard')}
                >
                    <IconDashboard />
                    <span>Chat</span>
                </button>
                <button 
                    className={`nav-item ${view === 'history' ? 'active' : ''}`}
                    onClick={() => handleNavigation('history')}
                >
                    <IconHistory />
                    <span>Chat History</span>
                </button>
                <button 
                    className={`nav-item ${view === 'agents' ? 'active' : ''}`}
                    onClick={() => handleNavigation('agents')}
                >
                    <IconAgents />
                    <span>Agents</span>
                </button>
                <button 
                    className={`nav-item ${view === 'settings' ? 'active' : ''}`}
                    onClick={() => handleNavigation('settings')}
                >
                    <IconSettings />
                    <span>Settings</span>
                </button>
            </nav>

            <div className="sidebar-footer">
                <div className="user-profile">
                    <div className="avatar">{(username?.[0] || 'U').toUpperCase()}</div>
                    <div className="user-info">
                        <span className="user-name">{username}</span>
                        <button className="logout-btn" onClick={handleLogout} title="Logout">Log out</button>
                    </div>
                </div>
            </div>
        </aside>

        <main className="main-content">
            {view === 'dashboard' && (
                <div className="chat-interface">
                    <header className="chat-header">
                        <h1>Arthur Prime</h1>
                        <p>At your service.</p>
                    </header>

                    <div className="chat-area">
                        {chatHistory.length === 0 && (
                            <div className="chat-message assistant">
                                <div className="message-icon"><IconCat /></div>
                                <div className="message-content">Hello, how can I help you?</div>
                            </div>
                        )}
                        {chatHistory.map((msg, i) => (
                            <div key={i} className={`chat-message ${msg.role}`}>
                                {msg.role === 'assistant' && <div className="message-icon"><IconCat /></div>}
                                <div className="message-content">{msg.content}</div>
                            </div>
                        ))}
                    </div>

                    <div className="input-area">
                        <form onSubmit={handleChatSubmit} className="chat-input-wrapper">
                            <input 
                                type="text" 
                                value={chatInput} 
                                onChange={(e) => setChatInput(e.target.value)} 
                                placeholder="Type your message..." 
                            />
                            <button type="submit" className="send-btn">
                                <Send size={20} />
                            </button>
                        </form>
                    </div>
                </div>
            )}
            
            {view === 'history' && (
                <div className="history-view" style={{ padding: '2rem', overflowY: 'auto', display: 'flex', flexDirection: 'column', height: '100%', boxSizing: 'border-box' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                        <h2>Chat History</h2>
                        <button 
                            onClick={handleDeleteSelected}
                            disabled={selectedSessions.length === 0}
                            style={{
                                backgroundColor: selectedSessions.length > 0 ? '#ef4444' : '#e2e8f0',
                                color: selectedSessions.length > 0 ? 'white' : '#94a3b8',
                                border: 'none',
                                padding: '0.5rem 1rem',
                                borderRadius: '4px',
                                cursor: selectedSessions.length > 0 ? 'pointer' : 'not-allowed',
                                fontWeight: '600'
                            }}
                        >
                            Delete Selected ({selectedSessions.length})
                        </button>
                    </div>

                    <div className="history-list" style={{ flex: 1, overflowY: 'auto' }}>
                        {fullHistory.map((session: any) => (
                            <div key={session.id} style={{ display: 'flex', gap: '1rem', marginBottom: '2rem', alignItems: 'flex-start' }}>
                                <input 
                                    type="checkbox" 
                                    checked={selectedSessions.includes(session.id)}
                                    onChange={() => toggleSession(session.id)}
                                    style={{ marginTop: '1rem', width: '20px', height: '20px' }}
                                />
                                <div style={{ flex: 1, border: '1px solid #e2e8f0', borderRadius: '8px', padding: '1rem', background: 'white' }}>
                                    <div style={{ borderBottom: '1px solid #eee', paddingBottom: '0.5rem', marginBottom: '1rem', color: '#64748b', fontSize: '0.9rem' }}>
                                        Session {session.id} • {session.created_at}
                                    </div>
                                    {session.messages.map((msg: any, i: number) => (
                                        <div key={i} style={{ marginBottom: '0.5rem', fontFamily: 'monospace', fontSize: '0.9rem' }}>
                                            <div style={{ color: '#94a3b8', fontSize: '0.8rem' }}>{msg.created_at}</div>
                                            <div><strong>{msg.role}:</strong> {msg.content}</div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>

                    <div style={{ marginTop: '2rem', textAlign: 'center' }}>
                        <button
                            onMouseDown={startNuke}
                            onMouseUp={cancelNuke}
                            onMouseLeave={cancelNuke}
                            onTouchStart={startNuke}
                            onTouchEnd={cancelNuke}
                            style={{
                                background: `linear-gradient(to right, #dc2626 ${nukeProgress}%, #ef4444 ${nukeProgress}%)`,
                                color: 'white',
                                border: 'none',
                                padding: '.5rem',
                                width: '100%',
                                maxWidth: '200px',
                                borderRadius: '4px',
                                fontSize: '1.2rem',
                                fontWeight: 'bold',
                                cursor: 'pointer',
                                transition: 'background 0.1s linear',
                                userSelect: 'none'
                            }}
                        >
                            {nukeProgress > 0 ? `HOLD TO NUKE... ${nukeProgress}%` : 'NUKE HISTORY'}
                        </button>
                        <p style={{ color: '#64748b', fontSize: '0.8rem', marginTop: '0.5rem' }}>Press and hold to delete all history</p>
                    </div>
                </div>
            )}

            {view === 'agents' && (
                <div className="agents-view" style={{ padding: '2rem', overflowY: 'auto', height: '100%', boxSizing: 'border-box' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                        <h2>Agents</h2>
                        <button 
                            onClick={() => setIsCreatingAgent(!isCreatingAgent)}
                            className="primary-btn"
                            style={{ 
                              width: 'auto',
                              padding: '.5rem'
                             }}
                        >
                            {isCreatingAgent ? 'Cancel' : 'Create Agent'}
                        </button>
                    </div>

                    {isCreatingAgent && (
                        <div style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', border: '1px solid #e2e8f0', marginBottom: '2rem' }}>
                            <h3>New Agent</h3>
                            <form onSubmit={handleCreateAgent}>
                                <div className="form-group">
                                    <label style={{ color: '#1e293b' }}>Name</label>
                                    <input 
                                        value={newAgentName} 
                                        onChange={e => setNewAgentName(e.target.value)} 
                                        placeholder="e.g. Creative Writer"
                                        style={{ background: 'white', color: '#1e293b', border: '1px solid #cbd5e1' }}
                                        required
                                    />
                                </div>
                                <div className="form-group">
                                    <label style={{ color: '#1e293b' }}>Prompt</label>
                                    <textarea 
                                        value={newAgentPrompt} 
                                        onChange={e => setNewAgentPrompt(e.target.value)} 
                                        placeholder="You are a helpful creative writer..."
                                        style={{ 
                                            width: '100%', 
                                            padding: '0.5rem', 
                                            borderRadius: '4px', 
                                            border: '1px solid #cbd5e1', 
                                            minHeight: '100px',
                                            fontFamily: 'inherit'
                                        }}
                                        required
                                    />
                                </div>
                                <button type="submit" className="primary-btn">Save Agent</button>
                            </form>
                        </div>
                    )}

                    <div className="agents-list" style={{ display: 'grid', gap: '1rem', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))' }}>
                        {agents.map(agent => (
                            <div key={agent.id} style={{ background: 'white', padding: '1.5rem', borderRadius: '8px', border: '1px solid #e2e8f0', position: 'relative' }}>
                                <button 
                                    onClick={() => handleDeleteAgent(agent.id)}
                                    style={{ position: 'absolute', top: '1rem', right: '1rem', background: 'none', border: 'none', cursor: 'pointer', color: '#94a3b8' }}
                                    title="Delete Agent"
                                >
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                                </button>
                                <h3 style={{ margin: '0 0 0.5rem 0' }}>{agent.name}</h3>
                                <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.5rem' }}>
                                    Created: {new Date(agent.created_at || Date.now()).toLocaleDateString()}
                                </div>
                                <div style={{ fontSize: '0.9rem', color: '#64748b', whiteSpace: 'pre-wrap', maxHeight: '150px', overflowY: 'auto' }}>
                                    {agent.prompt}
                                </div>
                            </div>
                        ))}
                        {agents.length === 0 && !isCreatingAgent && (
                            <div style={{ gridColumn: '1/-1', textAlign: 'center', color: '#94a3b8', padding: '2rem' }}>
                                No agents found. Create one to get started.
                            </div>
                        )}
                    </div>
                </div>
            )}
            
            {view !== 'dashboard' && view !== 'history' && view !== 'agents' && (
                <div className="content-placeholder">
                    <h2>{view.charAt(0).toUpperCase() + view.slice(1)}</h2>
                    <p>This section is under construction.</p>
                    {view === 'settings' && (
                         <button onClick={handleDeleteAccount} className="danger-btn">Delete Account</button>
                    )}
                </div>
            )}
        </main>
      </div>
    );
  }

  return (
    <div className="App auth-container">
      <h1>Arthur Prime</h1>
      <div className="card auth-card">
        <h2>{view === 'login' ? 'Login' : 'Create Account'}</h2>
        {error && <p className="error">{error}</p>}
        <form onSubmit={view === 'login' ? handleLogin : handleRegister}>
            <div className="form-group">
            <label>Username</label>
            <input value={username} onChange={e => setUsername(e.target.value)} required />
            </div>
            <div className="form-group">
            <label>Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} required />
            </div>
            <button type="submit" className="primary-btn">
                {view === 'login' ? 'Sign In' : 'Sign Up'}
            </button>
        </form>
        <p className="toggle-auth">
            {view === 'login' ? "New user? " : "Existing user? "}
            <button className="link-btn" onClick={() => {
                setView(view === 'login' ? 'register' : 'login');
                setError('');
            }}>
            {view === 'login' ? 'Create an account' : 'Log in'}
            </button>
        </p>
      </div>
    </div>
  );
}

export default App;
