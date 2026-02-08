import React from 'react';

interface AuthViewProps {
  view: 'login' | 'register';
  username: string;
  setUsername: (s: string) => void;
  password: string;
  setPassword: (s: string) => void;
  error: string;
  onLogin: (e: React.FormEvent) => void;
  onRegister: (e: React.FormEvent) => void;
  onToggleAuth: () => void;
}

export default function AuthView({
  view,
  username,
  setUsername,
  password,
  setPassword,
  error,
  onLogin,
  onRegister,
  onToggleAuth,
}: AuthViewProps) {
  return (
    <div className="App auth-container">
      <h1>Arthur Prime</h1>
      <div className="card auth-card">
        <h2>{view === 'login' ? 'Login' : 'Create Account'}</h2>
        {error && <p className="error">{error}</p>}
        <form onSubmit={view === 'login' ? onLogin : onRegister}>
          <div className="form-group">
            <label>Username</label>
            <input value={username} onChange={(e) => setUsername(e.target.value)} required />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          <button type="submit" className="primary-btn">
            {view === 'login' ? 'Sign In' : 'Sign Up'}
          </button>
        </form>
        <p className="toggle-auth">
          {view === 'login' ? 'New user? ' : 'Existing user? '}
          <button type="button" className="link-btn" onClick={onToggleAuth}>
            {view === 'login' ? 'Create an account' : 'Log in'}
          </button>
        </p>
      </div>
    </div>
  );
}
