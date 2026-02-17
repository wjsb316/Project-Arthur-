import { useState, useRef, useCallback } from 'react';

export function useVoiceRecording(
  token: string | null,
  currentSessionId: number | null,
  isNewSession: boolean,
  setCurrentSessionId: (id: number | null) => void,
  setIsNewSession: (v: boolean) => void
) {
  const [isRecording, setIsRecording] = useState(false);
  const [isVoiceProcessing, setIsVoiceProcessing] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const playbackAbortControllerRef = useRef<AbortController | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const audioSourcesRef = useRef<AudioBufferSourceNode[]>([]);

  const stopPlayback = useCallback(() => {
    playbackAbortControllerRef.current?.abort();
    audioSourcesRef.current.forEach((source) => {
      try {
        source.stop(0);
      } catch {
        // already stopped
      }
    });
    audioSourcesRef.current = [];
    if (audioContextRef.current?.state !== 'closed') {
      audioContextRef.current?.suspend?.();
    }
    setIsVoiceProcessing(false);
  }, []);

  const startRecording = useCallback(async () => {
    stopPlayback();
    if (
      !window.isSecureContext &&
      window.location.hostname !== 'localhost' &&
      window.location.hostname !== '127.0.0.1'
    ) {
      alert(
        'Microphone access blocked: You are accessing this site via an insecure connection (HTTP). Browsers require HTTPS for microphone access on mobile devices. Please use HTTPS or localhost.'
      );
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      console.error('Error accessing microphone:', err);
      let msg = 'Could not access microphone.';
      if (!window.isSecureContext) msg += ' This may be due to using HTTP instead of HTTPS.';
      alert(msg + ' Please check permissions and connection security.');
    }
  }, []);

  const stopRecording = useCallback(async () => {
    if (!mediaRecorderRef.current) return;
    const mediaRecorder = mediaRecorderRef.current;
    mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(chunksRef.current, { type: 'audio/wav' });
      setIsRecording(false);
      setIsVoiceProcessing(true);
      const formData = new FormData();
      formData.append('file', audioBlob, 'recording.wav');
      const abortController = new AbortController();
      playbackAbortControllerRef.current = abortController;
      const url = new URL('/api/chat/voice/stream', window.location.origin);
      if (isNewSession) {
        url.searchParams.set('new_session', 'true');
      } else if (currentSessionId != null) {
        url.searchParams.set('session_id', String(currentSessionId));
      }
      try {
        const res = await fetch(url.toString(), {
          method: 'POST',
          headers: { Authorization: `Bearer ${token}` },
          body: formData,
          signal: abortController.signal,
        });
        if (res.ok) {
          const sessionId = res.headers.get('X-Session-ID');
          const contentType = res.headers.get('Content-Type') ?? '';
          const transcribedText = res.headers.get('X-Transcribed-Text');
          const sampleRateHeader = res.headers.get('X-Audio-Sample-Rate');
          const sampleRate = sampleRateHeader ? parseInt(sampleRateHeader, 10) : 24000;
          if (sessionId) {
            setCurrentSessionId(parseInt(sessionId));
            setIsNewSession(false);
          }
          console.log('Transcribed:', transcribedText);
          if (contentType.includes('application/json')) {
            const data = await res.json();
            console.log('Voice response (TTS skipped):', data);
            setIsVoiceProcessing(false);
            return;
          }
          if (res.body) {
            try {
              const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
              audioContextRef.current = audioContext;
              const reader = res.body.getReader();
              let nextStartTime = 0;
              let chunkCount = 0;
              let playbackStarted = false;
              const bufferedAudioBuffers: AudioBuffer[] = [];
              let pendingBytes = new Uint8Array(0);

              const createAudioBuffer = (pcmData: Uint8Array): AudioBuffer | null => {
                if (pcmData.length === 0) return null;
                if (pcmData.length % 2 !== 0) return null;
                const alignedBuffer = new ArrayBuffer(pcmData.length);
                new Uint8Array(alignedBuffer).set(pcmData);
                const int16Array = new Int16Array(alignedBuffer);
                const float32Array = new Float32Array(int16Array.length);
                for (let i = 0; i < int16Array.length; i++) {
                  float32Array[i] = int16Array[i] / 32768.0;
                }
                const audioBuffer = audioContext.createBuffer(1, float32Array.length, sampleRate);
                audioBuffer.getChannelData(0).set(float32Array);
                return audioBuffer;
              };

              const scheduleAudioBuffer = (audioBuffer: AudioBuffer) => {
                const source = audioContext.createBufferSource();
                source.buffer = audioBuffer;
                source.connect(audioContext.destination);
                audioSourcesRef.current.push(source);
                const now = audioContext.currentTime;
                const startTime = Math.max(now + 0.01, nextStartTime);
                source.start(startTime);
                nextStartTime = startTime + audioBuffer.duration;
                chunkCount++;
              };

              const processBuffer = (): Uint8Array[] => {
                const chunks: Uint8Array[] = [];
                while (pendingBytes.length >= 4) {
                  const dataView = new DataView(pendingBytes.buffer, pendingBytes.byteOffset, 4);
                  const chunkLength = dataView.getUint32(0, true);
                  if (pendingBytes.length < 4 + chunkLength) break;
                  chunks.push(pendingBytes.slice(4, 4 + chunkLength));
                  pendingBytes = pendingBytes.slice(4 + chunkLength);
                }
                return chunks;
              };

              while (true) {
                const { done, value } = await reader.read();
                if (done) {
              for (const pcmData of processBuffer()) {
                if (pcmData.length === 0) continue;
                const audioBuffer = createAudioBuffer(pcmData);
                    if (audioBuffer) scheduleAudioBuffer(audioBuffer);
                  }
                  if (audioSourcesRef.current.length > 0) {
                    const lastScheduledEndTime = nextStartTime;
                    const now = audioContext.currentTime;
                    const timeUntilLastEnds = Math.max(0, lastScheduledEndTime - now);
                    const lastSource = audioSourcesRef.current[audioSourcesRef.current.length - 1];
                    lastSource.onended = () => setIsVoiceProcessing(false);
                    setTimeout(() => setIsVoiceProcessing(false), (timeUntilLastEnds * 1000) + 100);
                  } else {
                    setIsVoiceProcessing(false);
                  }
                  break;
                }
                if (value?.length) {
                  const newBuffer = new Uint8Array(pendingBytes.length + value.length);
                  newBuffer.set(pendingBytes);
                  newBuffer.set(value, pendingBytes.length);
                  pendingBytes = newBuffer;
              for (const pcmData of processBuffer()) {
                if (pcmData.length === 0) continue;
                const audioBuffer = createAudioBuffer(pcmData);
                    if (!audioBuffer) continue;
                    if (!playbackStarted) {
                      bufferedAudioBuffers.push(audioBuffer);
                      // Buffer ~0.5s of audio
                      const currentDuration = bufferedAudioBuffers.reduce((acc, b) => acc + b.duration, 0);
                      if (currentDuration >= 0.5) {
                        playbackStarted = true;
                        nextStartTime = audioContext.currentTime + 0.1;
                        for (const buf of bufferedAudioBuffers) scheduleAudioBuffer(buf);
                        bufferedAudioBuffers.length = 0;
                      }
                    } else {
                      scheduleAudioBuffer(audioBuffer);
                    }
                  }
                }
              }
            } catch (e) {
              if ((e as Error)?.name === 'AbortError') return;
              console.error('Error processing streaming audio:', e);
              setIsVoiceProcessing(false);
            }
          }
        } else {
          setIsVoiceProcessing(false);
        }
      } catch (e) {
        if ((e as Error)?.name !== 'AbortError') {
          console.error('Voice processing error:', e);
        }
        setIsVoiceProcessing(false);
      }
      mediaRecorder.stream.getTracks().forEach((track) => track.stop());
    };
    mediaRecorder.stop();
  }, [token, currentSessionId, isNewSession, setCurrentSessionId, setIsNewSession, stopPlayback]);

  const interruptPlayback = useCallback(() => {
    stopPlayback();
  }, [stopPlayback]);

  return { isRecording, isVoiceProcessing, startRecording, stopRecording, interruptPlayback };
}
