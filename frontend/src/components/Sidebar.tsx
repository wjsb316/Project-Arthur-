import React from 'react';
import {
  IconCat,
  IconMenu,
  IconDashboard,
  IconHistory,
  IconBrain,
  IconAgents,
  IconGuardrails,
  IconSettings,
  IconVoice,
} from './Icons';
import type { AppView } from '../types';

interface SidebarProps {
  view: AppView;
  setView: (v: AppView) => void;
  username: string;
  onLogout: () => void;
  isOpen: boolean;
  onClose: () => void;
}

const navItems: { view: AppView; Icon: React.FC; label: string }[] = [
  { view: 'voice', Icon: IconVoice, label: 'Voice' },
  { view: 'dashboard', Icon: IconDashboard, label: 'Chat' },
  { view: 'history', Icon: IconHistory, label: 'Chat History' },
  { view: 'memories', Icon: IconBrain, label: 'Memories' },
  { view: 'agents', Icon: IconAgents, label: 'Agents' },
  { view: 'guardrails', Icon: IconGuardrails, label: 'Guardrails' },
  { view: 'settings', Icon: IconSettings, label: 'Settings' },
];

export default function Sidebar({ view, setView, username, onLogout, isOpen, onClose }: SidebarProps) {
  return (
    <>
      {isOpen && <div className="sidebar-overlay" onClick={onClose} />}
      <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <IconCat />
          <div className="brand-text">
            <strong>Arthur Prime</strong>
            <br />
          </div>
        </div>
        <nav className="sidebar-nav">
          {navItems.map(({ view: v, Icon, label }) => (
            <button
              key={v}
              className={`nav-item ${view === v ? 'active' : ''}`}
              onClick={() => {
                setView(v);
                onClose();
              }}
            >
              <Icon />
              <span>{label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="user-profile">
            <div className="avatar">{(username?.[0] || 'U').toUpperCase()}</div>
            <div className="user-info">
              <span className="user-name">{username}</span>
              <button className="logout-btn" onClick={onLogout} title="Logout">
                Log out
              </button>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}

export function MobileHeader({ onMenuClick }: { onMenuClick: () => void }) {
  return (
    <header className="mobile-header">
      <button className="menu-btn" onClick={onMenuClick}>
        <IconMenu />
      </button>
      <span className="mobile-brand">Arthur Prime</span>
    </header>
  );
}
