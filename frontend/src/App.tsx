import React, { useState, useEffect } from 'react';
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

const IconHelp = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
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

const IconSend = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="22" y1="2" x2="11" y2="13"></line>
    <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
  </svg>
);

function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [view, setView] = useState<'login' | 'register' | 'dashboard' | 'help' | 'settings'>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  // Check valid token on load (optional: verify with backend)
  useEffect(() => {
    if (token) {
        setView('dashboard');
        fetch('/users/me', {
            headers: {
                'Authorization': `Bearer ${token}`,
                ...API_HEADERS
            }
        })
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

  const handleChatSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim()) return;
    
    const userMessage = { role: 'user', content: chatInput };
    setChatHistory(prev => [...prev, userMessage]);
    setChatInput('');

    try {
        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
                ...API_HEADERS
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
  };
  
  const handleDeleteAccount = async () => {
      if(!confirm("Are you sure? This cannot be undone.")) return;
      try {
          const res = await fetch('/users/me', {
              method: 'DELETE',
              headers: { 
                  'Authorization': `Bearer ${token}`,
                  ...API_HEADERS
              }
          });
          if(res.ok) handleLogout();
          else alert("Failed to delete");
      } catch(e) {
          alert("Error deleting account");
      }
  }

  if (['dashboard', 'help', 'settings'].includes(view)) {
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
                    onClick={() => {
                        setView('dashboard');
                        setIsSidebarOpen(false);
                    }}
                >
                    <IconDashboard />
                    <span>Chat</span>
                </button>
                <button 
                    className={`nav-item ${view === 'help' ? 'active' : ''}`}
                    onClick={() => {
                        setView('help');
                        setIsSidebarOpen(false);
                    }}
                >
                    <IconHelp />
                    <span>Help</span>
                </button>
                <button 
                    className={`nav-item ${view === 'settings' ? 'active' : ''}`}
                    onClick={() => {
                        setView('settings');
                        setIsSidebarOpen(false);
                    }}
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
                                <IconSend />
                            </button>
                        </form>
                    </div>
                </div>
            )}
            
            {view !== 'dashboard' && (
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
