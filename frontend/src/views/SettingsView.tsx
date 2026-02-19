import React from 'react';

interface SettingsViewProps {
  similarityThreshold: number;
  setSimilarityThreshold: (v: number) => void;
  configLoading: boolean;
  token: string | null;
  voiceCharactersUsed: number;
  onDeleteAccount: () => void;
}

export default function SettingsView({
  similarityThreshold,
  setSimilarityThreshold,
  configLoading,
  token,
  voiceCharactersUsed,
  onDeleteAccount,
}: SettingsViewProps) {
  const handleThresholdChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = parseInt(e.target.value, 10);
    setSimilarityThreshold(v);
    fetch('/api/config/', {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
        'X-Arthur-Client': 'Arthur-Prime-V1',
      },
      body: JSON.stringify({ similarity_threshold: v }),
    }).catch(console.error);
  };

  return (
    <div className="content-placeholder">
      <h2>Settings</h2>
      <div className="settings-section">
        <h3>Vector Search</h3>
        <div className="form-group">
          <label htmlFor="similarity-slider">
            Cosine similarity threshold: <strong>{similarityThreshold}</strong> (0–100)
          </label>
          <input
            id="similarity-slider"
            type="range"
            min={0}
            max={100}
            step={1}
            value={similarityThreshold}
            disabled={configLoading}
            onChange={handleThresholdChange}
          />
          <p className="form-hint">
            Minimum similarity for vector searches (memories, chat history). Guardrails are always included. Higher = stricter.
          </p>
        </div>
        <p>
          Total characters sent to voice model:{' '}
          <strong>{voiceCharactersUsed.toLocaleString()}</strong>
        </p>
        <button onClick={onDeleteAccount} className="danger-btn">
          Delete Account
        </button>
      </div>
    </div>
  );
}
