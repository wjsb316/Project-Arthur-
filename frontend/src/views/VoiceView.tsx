import { Mic } from 'lucide-react';
import { useState, useCallback } from 'react';
import { useOpenMicInterruption } from '../hooks/useOpenMicInterruption';
import Antigravity from '../Antigravity';
import { IconNewChat } from '../components/Icons';
import PipelineTimingDisplay from '../components/PipelineTimingDisplay';
import type { PipelineTiming } from '../types';

interface VoiceViewProps {
  token: string | null;
  isVoiceProcessing: boolean;
  isRecording: boolean;
  currentSessionId: number | null;
  isNewSession: boolean;
  setCurrentSessionId: (id: number | null) => void;
  setIsNewSession: (v: boolean) => void;
  onStartRecording: () => void;
  onStopRecording: () => void;
  onInterruptPlayback: () => void;
  onNewChat: () => void;
  pipelineTiming?: PipelineTiming | null;
  onTimingUpdate?: (timing: PipelineTiming) => void;
}

export default function VoiceView({
  token,
  isVoiceProcessing,
  isRecording,
  currentSessionId,
  isNewSession,
  setCurrentSessionId,
  setIsNewSession,
  onStartRecording,
  onStopRecording,
  onInterruptPlayback,
  onNewChat,
  pipelineTiming,
  onTimingUpdate,
}: VoiceViewProps) {
  const [isOpenMicEnabled, setIsOpenMicEnabled] = useState(false);
  const [isOpenMicProcessing, setIsOpenMicProcessing] = useState(false);

  // When Open Mic is enabled, continuously listen for speech, interrupt playback, record, and send to backend
  useOpenMicInterruption({
    enabled: isOpenMicEnabled,
    token,
    currentSessionId,
    isNewSession,
    setCurrentSessionId,
    setIsNewSession,
    onInterruptPlayback,
    onVoiceProcessingChange: setIsOpenMicProcessing,
    onTimingUpdate,
  });

  const handleToggleOpenMic = useCallback(() => {
    setIsOpenMicEnabled((prev) => !prev);
  }, []);

  const handlePressStart = useCallback(() => {
    if (isOpenMicEnabled) return;
    onStartRecording();
  }, [isOpenMicEnabled, onStartRecording]);

  const handlePressStop = useCallback(() => {
    if (isOpenMicEnabled) return;
    onStopRecording();
  }, [isOpenMicEnabled, onStopRecording]);

  return (
    <div
      className="voice-interface"
      style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%', position: 'relative' }}
    >
      <div
        style={{
          position: 'absolute',
          top: '1rem',
          right: '1rem',
          zIndex: 10,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'flex-end',
          gap: '0.4rem',
        }}
      >
        <button
          onClick={onNewChat}
          title="Start New Chat"
          style={{
            background: 'rgba(255,255,255,0.85)',
            border: '1px solid rgba(255,255,255,0.6)',
            borderRadius: '8px',
            padding: '0.5rem 0.75rem',
            cursor: 'pointer',
            color: '#333',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            backdropFilter: 'blur(8px)',
            boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
            transition: 'background 0.2s ease',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,1)')}
          onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.85)')}
        >
          <IconNewChat />
          <span style={{ fontSize: '0.9rem', fontWeight: 500 }}>New Chat</span>
        </button>
        <PipelineTimingDisplay timing={pipelineTiming ?? null} dark={true} />
      </div>
      <div style={{ width: '100%', height: '100%', position: 'absolute', top: 0, left: 0, zIndex: 1 }}>
        <Antigravity
          count={1000}
          magnetRadius={21}
          ringRadius={5}
          waveSpeed={5}
          waveAmplitude={5}
          particleSize={1.3}
          lerpSpeed={0.02}
          color="#616375"
          autoAnimate={false}
          particleVariance={0.5}
          rotationSpeed={0.1}
          depthFactor={1}
          pulseSpeed={10}
          particleShape="sphere"
          fieldStrength={10}
          isProcessing={isVoiceProcessing || isOpenMicProcessing}
        />
      </div>
      <div
        style={{
          position: 'absolute',
          bottom: '40px',
          left: '50%',
          transform: 'translateX(-50%)',
          zIndex: 10,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '1rem',
        }}
      >
        <button
          onMouseDown={handlePressStart}
          onMouseUp={handlePressStop}
          onMouseLeave={handlePressStop}
          onTouchStart={handlePressStart}
          onTouchEnd={handlePressStop}
          disabled={isOpenMicEnabled}
          style={{
            width: '80px',
            height: '80px',
            borderRadius: '50%',
            border: 'none',
            background: isRecording ? '#ef4444' : 'white',
            color: isRecording ? 'white' : '#333',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: isOpenMicEnabled ? 'not-allowed' : 'pointer',
            boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
            transition: 'all 0.2s ease',
            transform: isRecording ? 'scale(1.1)' : 'scale(1)',
            opacity: isOpenMicEnabled ? 0.6 : 1,
          }}
        >
          <Mic size={32} />
        </button>
        <span
          style={{
            color: 'white',
            textShadow: '0 1px 2px rgba(0,0,0,0.5)',
            fontWeight: 500,
          }}
        >
          {isRecording ? 'Listening...' : 'Hold to Speak'}
        </span>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            color: 'white',
            textShadow: '0 1px 2px rgba(0,0,0,0.5)',
            fontWeight: 500,
          }}
        >
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={isOpenMicEnabled}
              onChange={handleToggleOpenMic}
              style={{ width: '16px', height: '16px' }}
            />
            <span>Open Mic (interrupt on speech)</span>
          </label>
        </div>
      </div>
    </div>
  );
}
