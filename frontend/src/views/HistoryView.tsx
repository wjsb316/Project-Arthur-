import ReactMarkdown from 'react-markdown';
import type { HistorySession } from '../types';

interface HistoryViewProps {
  filteredHistory: HistorySession[];
  historySearch: string;
  setHistorySearch: (s: string) => void;
  selectedSessions: number[];
  toggleSession: (id: number) => void;
  nukeProgress: number;
  onDeleteSelected: () => void;
  onLoadSession: (session: HistorySession) => void;
  onNukeMouseDown: () => void;
  onNukeMouseUp: () => void;
  onNukeMouseLeave: () => void;
  onNukeTouchStart: () => void;
  onNukeTouchEnd: () => void;
}

const cardStyle = {
  flex: 1,
  border: '1px solid #e2e8f0',
  borderRadius: '8px',
  padding: '1rem',
  background: 'white',
};

export default function HistoryView({
  filteredHistory,
  historySearch,
  setHistorySearch,
  selectedSessions,
  toggleSession,
  nukeProgress,
  onDeleteSelected,
  onLoadSession,
  onNukeMouseDown,
  onNukeMouseUp,
  onNukeMouseLeave,
  onNukeTouchStart,
  onNukeTouchEnd,
}: HistoryViewProps) {
  return (
    <div
      className="history-view"
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
        <h2>Chat History</h2>
        <button
          onClick={onDeleteSelected}
          disabled={selectedSessions.length === 0}
          style={{
            backgroundColor: selectedSessions.length > 0 ? '#ef4444' : '#e2e8f0',
            color: selectedSessions.length > 0 ? 'white' : '#94a3b8',
            border: 'none',
            padding: '0.5rem 1rem',
            borderRadius: '4px',
            cursor: selectedSessions.length > 0 ? 'pointer' : 'not-allowed',
            fontWeight: '600',
          }}
        >
          Delete Selected ({selectedSessions.length})
        </button>
      </div>
      <div style={{ marginBottom: '2rem' }}>
        <input
          type="text"
          value={historySearch}
          onChange={(e) => setHistorySearch(e.target.value)}
          placeholder="Search history..."
          style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid #cbd5e1' }}
        />
      </div>
      <div className="history-list" style={{ flex: 1, overflowY: 'auto' }}>
        {filteredHistory.map((session) => (
          <div
            key={session.id}
            style={{ display: 'flex', gap: '1rem', marginBottom: '2rem', alignItems: 'flex-start' }}
          >
            <input
              type="checkbox"
              checked={selectedSessions.includes(session.id)}
              onChange={() => toggleSession(session.id)}
              style={{ marginTop: '1rem', width: '20px', height: '20px' }}
            />
            <div style={cardStyle}>
              <div
                style={{
                  borderBottom: '1px solid #eee',
                  paddingBottom: '0.5rem',
                  marginBottom: '1rem',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <span style={{ color: '#64748b', fontSize: '0.9rem' }}>
                  Session {session.id} • {session.created_at}
                </span>
                <button
                  onClick={() => onLoadSession(session)}
                  style={{
                    background: '#3b82f6',
                    color: 'white',
                    border: 'none',
                    padding: '0.25rem 0.75rem',
                    borderRadius: '4px',
                    fontSize: '0.8rem',
                    fontWeight: '500',
                    cursor: 'pointer',
                  }}
                >
                  Continue
                </button>
              </div>
              {session.messages.map((msg, i) => (
                <div
                  key={i}
                  style={{ marginBottom: '0.5rem', fontFamily: 'monospace', fontSize: '0.9rem' }}
                >
                  <div style={{ color: '#94a3b8', fontSize: '0.8rem' }}>{msg.created_at}</div>
                  <div>
                    <strong>{msg.role}:</strong>{' '}
                    <ReactMarkdown components={{ p: ({ children }) => <span>{children}</span> }}>
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
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
          {nukeProgress > 0 ? `HOLD TO NUKE... ${nukeProgress}%` : 'NUKE HISTORY'}
        </button>
        <p style={{ color: '#64748b', fontSize: '0.8rem', marginTop: '0.5rem' }}>
          Press and hold to delete all history
        </p>
      </div>
    </div>
  );
}
