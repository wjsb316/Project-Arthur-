import React from 'react';
import { Pencil } from 'lucide-react';
import type { Guardrail } from '../types';

interface GuardrailsViewProps {
  guardrails: Guardrail[];
  isCreatingGuardrail: boolean;
  setIsCreatingGuardrail: (v: boolean) => void;
  newGuardrailName: string;
  setNewGuardrailName: (s: string) => void;
  newGuardrailPrompt: string;
  setNewGuardrailPrompt: (s: string) => void;
  editingGuardrail: Guardrail | null;
  setEditingGuardrail: (g: Guardrail | null) => void;
  editGuardrailName: string;
  setEditGuardrailName: (s: string) => void;
  editGuardrailPrompt: string;
  setEditGuardrailPrompt: (s: string) => void;
  onCreateGuardrail: (e: React.FormEvent) => void;
  onUpdateGuardrail: (e: React.FormEvent) => void;
  onDeleteGuardrail: (id: number) => void;
}

export default function GuardrailsView({
  guardrails,
  isCreatingGuardrail,
  setIsCreatingGuardrail,
  newGuardrailName,
  setNewGuardrailName,
  newGuardrailPrompt,
  setNewGuardrailPrompt,
  editingGuardrail,
  editGuardrailName,
  setEditGuardrailName,
  editGuardrailPrompt,
  setEditGuardrailPrompt,
  setEditingGuardrail,
  onCreateGuardrail,
  onUpdateGuardrail,
  onDeleteGuardrail,
}: GuardrailsViewProps) {
  return (
    <div
      className="guardrails-view"
      style={{ padding: '2rem', overflowY: 'auto', height: '100%', boxSizing: 'border-box' }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h2>Guardrails</h2>
        <button
          onClick={() => setIsCreatingGuardrail(!isCreatingGuardrail)}
          className="primary-btn"
          style={{ width: 'auto', padding: '.5rem' }}
        >
          {isCreatingGuardrail ? 'Cancel' : 'Create Guardrail'}
        </button>
      </div>
      {isCreatingGuardrail && (
        <div
          style={{
            background: 'white',
            padding: '1.5rem',
            borderRadius: '8px',
            border: '1px solid #e2e8f0',
            marginBottom: '2rem',
          }}
        >
          <h3>New Guardrail</h3>
          <form onSubmit={onCreateGuardrail}>
            <div className="form-group">
              <label style={{ color: '#1e293b' }}>Name</label>
              <input
                value={newGuardrailName}
                onChange={(e) => setNewGuardrailName(e.target.value)}
                placeholder="e.g. Safety Filter"
                style={{ background: 'white', color: '#1e293b', border: '1px solid #cbd5e1' }}
                required
              />
            </div>
            <div className="form-group">
              <label style={{ color: '#1e293b' }}>Rule/Prompt</label>
              <textarea
                value={newGuardrailPrompt}
                onChange={(e) => setNewGuardrailPrompt(e.target.value)}
                placeholder="Never provide harmful, illegal, or unethical advice..."
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
              Save Guardrail
            </button>
          </form>
        </div>
      )}
      {editingGuardrail && (
        <div
          style={{
            background: 'white',
            padding: '1.5rem',
            borderRadius: '8px',
            border: '1px solid #e2e8f0',
            marginBottom: '2rem',
          }}
        >
          <h3>Edit Guardrail</h3>
          <form onSubmit={onUpdateGuardrail}>
            <div className="form-group">
              <label style={{ color: '#1e293b' }}>Name</label>
              <input
                value={editGuardrailName}
                onChange={(e) => setEditGuardrailName(e.target.value)}
                style={{ background: 'white', color: '#1e293b', border: '1px solid #cbd5e1' }}
                required
              />
            </div>
            <div className="form-group">
              <label style={{ color: '#1e293b' }}>Rule/Prompt</label>
              <textarea
                value={editGuardrailPrompt}
                onChange={(e) => setEditGuardrailPrompt(e.target.value)}
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
              Update Guardrail
            </button>
          </form>
        </div>
      )}
      <div
        className="guardrails-list"
        style={{ display: 'grid', gap: '1rem', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))' }}
      >
        {guardrails.map((guardrail) => (
          <div
            key={guardrail.id}
            style={{
              background: 'white',
              padding: '1.5rem',
              borderRadius: '8px',
              border: '1px solid #e2e8f0',
              position: 'relative',
            }}
          >
            <button
              onClick={() => onDeleteGuardrail(guardrail.id)}
              style={{
                position: 'absolute',
                top: '1rem',
                right: '1rem',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: '#94a3b8',
              }}
              title="Delete Guardrail"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
            <button
              onClick={() => {
                setEditingGuardrail(guardrail);
                setEditGuardrailName(guardrail.name);
                setEditGuardrailPrompt(guardrail.prompt);
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
              title="Edit Guardrail"
            >
              <Pencil size={16} />
            </button>
            <h3 style={{ margin: '0 0 0.5rem 0' }}>{guardrail.name}</h3>
            <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '0.5rem' }}>
              Created: {new Date(guardrail.created_at || Date.now()).toLocaleDateString()}
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
              {guardrail.prompt}
            </div>
          </div>
        ))}
        {guardrails.length === 0 && !isCreatingGuardrail && (
          <div style={{ gridColumn: '1/-1', textAlign: 'center', color: '#94a3b8', padding: '2rem' }}>
            No guardrails found. Create one to get started.
          </div>
        )}
      </div>
    </div>
  );
}
