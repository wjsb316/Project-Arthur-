import React, { useState, useEffect } from 'react';
import './App.css';

const API_HEADERS = {
    'X-Arthur-Client': 'Arthur-Prime-V1'
};

function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  const [view, setView] = useState<'login' | 'register' | 'dashboard'>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  // Check valid token on load (optional: verify with backend)
  useEffect(() => {
    if (token) setView('dashboard');
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
            // const data = await res.json();
            // setChatHistory(prev => [...prev, { role: 'assistant', content: data.response }]);
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

  if (view === 'dashboard') {
    return (
      <div className="App">
        <header className="header">
            <h1>Arthur Prime</h1>
            <div className="user-controls">
                <span>{username}</span>
                <button onClick={handleLogout}>Logout</button>
            </div>
        </header>
        
        <main className="dashboard">
            <div className="card">
                <h2>Account Management</h2>
                <p>Welcome to your dashboard.</p>
                <button onClick={handleDeleteAccount} className="danger-btn">Delete Account</button>
            </div>
            
            <div className="card features">
                <h2>Assistant</h2>
                <div className="chat-container">
                    <div className="chat-history">
                        {chatHistory.map((msg, i) => (
                            <div key={i} className={`chat-message ${msg.role}`}>
                                <strong>{msg.role}: </strong>{msg.content}
                            </div>
                        ))}
                    </div>
                    <form onSubmit={handleChatSubmit} className="chat-input-form">
                        <input 
                            type="text" 
                            value={chatInput} 
                            onChange={(e) => setChatInput(e.target.value)} 
                            placeholder="Type a message..." 
                            className="chat-input"
                        />
                        <button type="submit" className="chat-submit-btn">Send</button>
                    </form>
                </div>
            </div>
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
