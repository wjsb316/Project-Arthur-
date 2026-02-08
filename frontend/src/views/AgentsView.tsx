import React from 'react';
import { Pencil } from 'lucide-react';
import type { Agent } from '../types';

interface AgentsViewProps {
  agents: Agent[];
  isCreatingAgent: boolean;
  setIsCreatingAgent: (v: boolean) => void;
  newAgentName: string;
  setNewAgentName: (s: string) => void;
  newAgentPrompt: string;
  setNewAgentPrompt: (s: string) => void;
  editingAgent: Agent | null;
  setEditingAgent: (a: Agent | null) => void;
  editAgentName: string;
  setEditAgentName: (s: string) => void;
  editAgentPrompt: string;
  setEditAgentPrompt: (s: string) => void;
  onCreateAgent: (e: React.FormEvent) => void;
  onUpdateAgent: (e: React.FormEvent) => void;
  onDeleteAgent: (id: number) => void;
}

export default function AgentsView({
  agents,
  isCreatingAgent,
  setIsCreatingAgent,
  newAgentName,
  setNewAgentName,
  newAgentPrompt,
  setNewAgentPrompt,
  editingAgent,
  editAgentName,
  setEditAgentName,
  editAgentPrompt,
  setEditAgentPrompt,
  setEditingAgent,
  onCreateAgent,
  onUpdateAgent,
  onDeleteAgent,
}: AgentsViewProps) {
  return (
    <div
      className="agents-view"
      style={{ padding: '2rem', overflowY: 'auto', height: '100%', boxSizing: 'border-box' }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h2>Agents</h2>
        <button
          onClick={() => setIsCreatingAgent(!isCreatingAgent)}
          className="primary-btn"
          style={{ width: 'auto', padding: '.5rem' }}
        >
          {isCreatingAgent ? 'Cancel' : 'Create Agent'}
        </button>
      </div>
      {isCreatingAgent && (
        <div
          style={{
            background: 'white',
            padding: '1.5rem',
            borderRadius: '8px',
            border: '1px solid #e2e8f0',
            marginBottom: '2rem',
          }}
        >
          <h3>New Agent</h3>
          <form onSubmit={onCreateAgent}>
            <div className="form-group">
              <label style={{ color: '#1e293b' }}>Name</label>
              <input
                value={newAgentName}
                onChange={(e) => setNewAgentName(e.target.value)}
                placeholder="e.g. Creative Writer"
                style={{ background: 'white', color: '#1e293b', border: '1px solid #cbd5e1' }}
                required
              />
            </div>
            <div className="form-group">
              <label style={{ color: '#1e293b' }}>Prompt</label>
              <textarea
                value={newAgentPrompt}
                onChange={(e) => setNewAgentPrompt(e.target.value)}
                placeholder="You are a helpful creative writer..."
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '4px',
                  border: '1px solid #cbd5e1',
                  minHeight: '100px',
                  fontFamily: 'inherit',
                }}
                required
              />
            </div>
            <button type="submit" className="primary-btn">
              Save Agent
            </button>
          </form>
        </div>
      )}
      {editingAgent && (
        <div
          style={{
            background: 'white',
            padding: '1.5rem',
            borderRadius: '8px',
            border: '1px solid #e2e8f0',
            marginBottom: '2rem',
          }}
        >
          <h3>Edit Agent</h3>
          <form onSubmit={onUpdateAgent}>
            <div className="form-group">
              <label style={{ color: '#1e293b' }}>Name</label>
              <input
                value={editAgentName}
                onChange={(e) => setEditAgentName(e.target.value)}
                style={{ background: 'white', color: '#1e293b', border: '1px solid #cbd5e1' }}
                required
              />
            </div>
            <div className="form-group">
              <label style={{ color: '#1e293b' }}>Prompt</label>
              <textarea
                value={editAgentPrompt}
                onChange={(e) => setEditAgentPrompt(e.target.value)}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  borderRadius: '4px',
                  border: '1px solid #cbd5e1',
                  minHeight: '100px',
                  fontFamily: 'inherit',
                }}
                required
              />
            </div>
            <button type="submit" className="primary-btn">
              Update Agent
            </button>
          </form>
        </div>
      )}
      <div
        className="agents-list"
        style={{ display: 'grid', gap: '1rem', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))' }}
      >
        {agents.map((agent) => (
          <div
            key={agent.id}
            style={{
              background: 'white',
              padding: '1.5rem',
              borderRadius: '8px',
              border: '1px solid #e2e8f0',
              position: 'relative',
            }}
          >
            <button
              onClick={() => onDeleteAgent(agent.id)}
              style={{
                position: 'absolute',
                top: '1rem',
                right: '1rem',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: '#94a3b8',
              }}
              title="Delete Agent"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
            <button
              onClick={() => {
                setEditingAgent(agent);
                setEditAgentName(agent.name);
                setEditAgentPrompt(agent.prompt);
              }}
              style={{
                position: 'absolute',
                top: '1rem',
                right: '3rem',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: '#94a3b8',
              }}
              title="Edit Agent"
            >
              <Pencil size={16} />
            </button>
            <h3 style={{ margin: '0 0 0.5rem 0' }}>{agent.name}</h3>
            <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.5rem' }}>
              Created: {new Date(agent.created_at || Date.now()).toLocaleDateString()}
            </div>
            <div
              style={{
                fontSize: '0.9rem',
                color: '#64748b',
                whiteSpace: 'pre-wrap',
                maxHeight: '150px',
                overflowY: 'auto',
              }}
            >
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
  );
}
