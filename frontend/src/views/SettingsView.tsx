import React from 'react';
import { useTheme, type ThemePreference } from '../theme';

interface SettingsViewProps {
  similarityThreshold: number;
  setSimilarityThreshold: (v: number) => void;
  configLoading: boolean;
  token: string | null;
  voiceCharactersUsed: number;
  onDeleteAccount: () => void;
}

const THEME_OPTIONS: { value: ThemePreference; label: string }[] = [
  { value: 'light', label: 'Light' },
  { value: 'dark', label: 'Dark' },
  { value: 'system', label: 'System' },
];

export default function SettingsView({
  similarityThreshold,
  setSimilarityThreshold,
  configLoading,
  token,
  voiceCharactersUsed,
  onDeleteAccount,
}: SettingsViewProps) {
  const { preference, setPreference } = useTheme();

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
    <div className="content-placeholder settings-content">
      <h2>Settings</h2>
      <div className="settings-section" style={{ width: '100%', maxWidth: '420px' }}>
        <h3>Appearance</h3>
        <p className="form-hint" style={{ marginBottom: '0.75rem' }}>
          Theme applies across the app. System follows your OS light/dark setting.
        </p>
        <div className="theme-options" role="radiogroup" aria-label="Color theme">
          {THEME_OPTIONS.map(({ value, label }) => (
            <label key={value} className="theme-option">
              <input
                type="radio"
                name="theme"
                value={value}
                checked={preference === value}
                onChange={() => setPreference(value)}
              />
              {label}
            </label>
          ))}
        </div>
      </div>
      <div className="settings-section" style={{ width: '100%', maxWidth: '420px' }}>
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
        <p style={{ color: 'var(--text-color)' }}>
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
