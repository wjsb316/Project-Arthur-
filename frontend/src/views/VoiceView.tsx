import { Mic } from 'lucide-react';
import Antigravity from '../Antigravity';

interface VoiceViewProps {
  token: string | null;
  isVoiceProcessing: boolean;
  isRecording: boolean;
  onStartRecording: () => void;
  onStopRecording: () => void;
}

export default function VoiceView({
  isVoiceProcessing,
  isRecording,
  onStartRecording,
  onStopRecording,
}: VoiceViewProps) {
  return (
    <div
      className="voice-interface"
      style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%', position: 'relative' }}
    >
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
          isProcessing={isVoiceProcessing}
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
          onMouseDown={onStartRecording}
          onMouseUp={onStopRecording}
          onMouseLeave={onStopRecording}
          onTouchStart={onStartRecording}
          onTouchEnd={onStopRecording}
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
            cursor: 'pointer',
            boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
            transition: 'all 0.2s ease',
            transform: isRecording ? 'scale(1.1)' : 'scale(1)',
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
      </div>
    </div>
  );
}
