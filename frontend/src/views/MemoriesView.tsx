import React from 'react';
import { Pencil } from 'lucide-react';
import type { Memory } from '../types';

interface MemoriesViewProps {
  filteredMemories: Memory[];
  memorySearch: string;
  setMemorySearch: (s: string) => void;
  selectedMemories: number[];
  toggleMemory: (id: number) => void;
  isCreatingMemory: boolean;
  setIsCreatingMemory: (v: boolean) => void;
  newMemoryContent: string;
  setNewMemoryContent: (s: string) => void;
  newMemoryKind: string;
  setNewMemoryKind: (s: string) => void;
  editingMemory: Memory | null;
  setEditingMemory: (m: Memory | null) => void;
  editMemoryContent: string;
  setEditMemoryContent: (s: string) => void;
  editMemoryKind: string;
  setEditMemoryKind: (s: string) => void;
  onCreateMemory: (e: React.FormEvent) => void;
  onUpdateMemory: (e: React.FormEvent) => void;
  onDeleteSelected: () => void;
  nukeProgress: number;
  onNukeMouseDown: () => void;
  onNukeMouseUp: () => void;
  onNukeMouseLeave: () => void;
  onNukeTouchStart: () => void;
  onNukeTouchEnd: () => void;
}

const selectStyles: React.CSSProperties = {
  width: '100%',
  padding: '0.5rem',
  borderRadius: '4px',
  border: '1px solid var(--form-input-border)',
  background: 'var(--form-input-bg)',
  color: 'var(--text-color)',
  marginBottom: '1rem',
};

const textareaStyles: React.CSSProperties = {
  width: '100%',
  padding: '0.5rem',
  borderRadius: '4px',
  border: '1px solid var(--form-input-border)',
  minHeight: '100px',
  fontFamily: 'inherit',
  background: 'var(--form-input-bg)',
  color: 'var(--text-color)',
};

export default function MemoriesView({
  filteredMemories,
  memorySearch,
  setMemorySearch,
  selectedMemories,
  toggleMemory,
  isCreatingMemory,
  setIsCreatingMemory,
  newMemoryContent,
  setNewMemoryContent,
  newMemoryKind,
  setNewMemoryKind,
  editingMemory,
  editMemoryContent,
  setEditMemoryContent,
  editMemoryKind,
  setEditMemoryKind,
  setEditingMemory,
  onCreateMemory,
  onUpdateMemory,
  onDeleteSelected,
  nukeProgress,
  onNukeMouseDown,
  onNukeMouseUp,
  onNukeMouseLeave,
  onNukeTouchStart,
  onNukeTouchEnd,
}: MemoriesViewProps) {
  return (
    <div
      className="memories-view"
      style={{
        padding: '2rem',
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        boxSizing: 'border-box',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2>Memories</h2>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            onClick={onDeleteSelected}
            disabled={selectedMemories.length === 0}
            style={{
              backgroundColor: selectedMemories.length > 0 ? '#ef4444' : 'var(--send-btn-bg)',
              color: selectedMemories.length > 0 ? 'white' : 'var(--muted-foreground-2)',
              border: 'none',
              padding: '0.5rem 1rem',
              borderRadius: '4px',
              cursor: selectedMemories.length > 0 ? 'pointer' : 'not-allowed',
              fontWeight: '600',
            }}
          >
            Delete Selected ({selectedMemories.length})
          </button>
          <button
            onClick={() => setIsCreatingMemory(!isCreatingMemory)}
            className="primary-btn"
            style={{ width: 'auto', padding: '.5rem' }}
          >
            {isCreatingMemory ? 'Cancel' : 'Add Memory'}
          </button>
        </div>
      </div>
      <div style={{ marginBottom: '2rem' }}>
        <input
          type="text"
          value={memorySearch}
          onChange={(e) => setMemorySearch(e.target.value)}
          placeholder="Search memories..."
          style={{
            width: '100%',
            padding: '0.5rem',
            borderRadius: '4px',
            border: '1px solid var(--form-input-border)',
            background: 'var(--form-input-bg)',
            color: 'var(--text-color)',
          }}
        />
      </div>
      {isCreatingMemory && (
        <div
          style={{
            background: 'var(--form-card-bg)',
            padding: '1.5rem',
            borderRadius: '8px',
            border: '1px solid var(--form-border-subtle)',
            marginBottom: '2rem',
          }}
        >
          <h3>New Memory</h3>
          <form onSubmit={onCreateMemory}>
            <div className="form-group">
              <label style={{ color: 'var(--form-label)' }}>Type</label>
              <select
                value={newMemoryKind}
                onChange={(e) => setNewMemoryKind(e.target.value)}
                style={selectStyles}
              >
                <option value="fact">Fact</option>
                <option value="episode">Episode</option>
                <option value="open_loop">Open Loop</option>
              </select>
            </div>
            <div className="form-group">
              <label style={{ color: 'var(--form-label)' }}>Content</label>
              <textarea
                value={newMemoryContent}
                onChange={(e) => setNewMemoryContent(e.target.value)}
                placeholder="I like coffee with oat milk..."
                style={textareaStyles}
                required
              />
            </div>
            <button type="submit" className="primary-btn">
              Save Memory
            </button>
          </form>
        </div>
      )}
      {editingMemory && (
        <div
          style={{
            background: 'var(--form-card-bg)',
            padding: '1.5rem',
            borderRadius: '8px',
            border: '1px solid var(--form-border-subtle)',
            marginBottom: '2rem',
          }}
        >
          <h3>Edit Memory</h3>
          <form onSubmit={onUpdateMemory}>
            <div className="form-group">
              <label style={{ color: 'var(--form-label)' }}>Type</label>
              <select value={editMemoryKind} onChange={(e) => setEditMemoryKind(e.target.value)} style={selectStyles}>
                <option value="fact">Fact</option>
                <option value="episode">Episode</option>
                <option value="open_loop">Open Loop</option>
              </select>
            </div>
            <div className="form-group">
              <label style={{ color: 'var(--form-label)' }}>Content</label>
              <textarea
                value={editMemoryContent}
                onChange={(e) => setEditMemoryContent(e.target.value)}
                style={textareaStyles}
                required
              />
            </div>
            <button type="submit" className="primary-btn">
              Update Memory
            </button>
          </form>
        </div>
      )}
      <div className="memories-list" style={{ flex: 1, overflowY: 'auto' }}>
        {filteredMemories.map((memory) => (
          <div
            key={memory.id}
            style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', alignItems: 'flex-start' }}
          >
            <input
              type="checkbox"
              checked={selectedMemories.includes(memory.id)}
              onChange={() => toggleMemory(memory.id)}
              style={{ marginTop: '1.5rem', width: '20px', height: '20px', flexShrink: 0 }}
            />
            <div
              style={{
                flex: 1,
                background: 'var(--form-card-bg)',
                padding: '1.5rem',
                borderRadius: '8px',
                border: '1px solid var(--form-border-subtle)',
                position: 'relative',
              }}
            >
              <button
                onClick={() => {
                  setEditingMemory(memory);
                  setEditMemoryContent(memory.content);
                  setEditMemoryKind(memory.kind);
                }}
                style={{
                  position: 'absolute',
                  top: '0.5rem',
                  right: '0.5rem',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: 'var(--muted-foreground-2)',
                }}
                title="Edit Memory"
              >
                <Pencil size={16} />
              </button>
              <div style={{ fontSize: '0.8rem', color: 'var(--muted-foreground-2)', marginBottom: '0.5rem' }}>
                {new Date(memory.created_at).toLocaleDateString()} • {memory.kind}
              </div>
              <div
                style={{
                  fontSize: '0.9rem',
                  color: 'var(--muted-foreground)',
                  whiteSpace: 'pre-wrap',
                  maxHeight: '150px',
                  overflowY: 'auto',
                }}
              >
                {memory.content}
              </div>
            </div>
          </div>
        ))}
        {filteredMemories.length === 0 && !isCreatingMemory && (
          <div style={{ textAlign: 'center', color: 'var(--muted-foreground-2)', padding: '2rem' }}>No memories found.</div>
        )}
      </div>
      <div style={{ marginTop: '2rem', textAlign: 'center' }}>
        <button
          onMouseDown={onNukeMouseDown}
          onMouseUp={onNukeMouseUp}
          onMouseLeave={onNukeMouseLeave}
          onTouchStart={onNukeTouchStart}
          onTouchEnd={onNukeTouchEnd}
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
            userSelect: 'none',
          }}
        >
          {nukeProgress > 0 ? `HOLD TO NUKE... ${nukeProgress}%` : 'NUKE MEMORIES'}
        </button>
        <p style={{ color: 'var(--muted-foreground)', fontSize: '0.8rem', marginTop: '0.5rem' }}>
          Press and hold to delete all memories
        </p>
      </div>
    </div>
  );
}
