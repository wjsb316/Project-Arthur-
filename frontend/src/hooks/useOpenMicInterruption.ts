import { useEffect, useRef, useCallback } from 'react';

interface UseOpenMicInterruptionOptions {
  enabled: boolean;
  token: string | null;
  currentSessionId: number | null;
  isNewSession: boolean;
  setCurrentSessionId: (id: number | null) => void;
  setIsNewSession: (v: boolean) => void;
  onInterruptPlayback: () => void;
  onVoiceProcessingChange: (processing: boolean) => void;
}

/**
 * Listens to the microphone while `enabled` is true, detects speech using VAD (Voice Activity Detection),
 * interrupts playback when speech starts, records the audio, and sends it to the backend when speech ends.
 */
export function useOpenMicInterruption({
  enabled,
  token,
  currentSessionId,
  isNewSession,
  setCurrentSessionId,
  setIsNewSession,
  onInterruptPlayback,
  onVoiceProcessingChange,
}: UseOpenMicInterruptionOptions) {
  const vadAudioContextRef = useRef<AudioContext | null>(null); // For VAD (Voice Activity Detection)
  const playbackAudioContextRef = useRef<AudioContext | null>(null); // For playback
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const recordingChunksRef = useRef<Blob[]>([]);
  const isRecordingRef = useRef(false);
  const playbackAbortControllerRef = useRef<AbortController | null>(null);
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
    if (playbackAudioContextRef.current?.state !== 'closed') {
      playbackAudioContextRef.current?.suspend?.();
    }
    onVoiceProcessingChange(false);
  }, [onVoiceProcessingChange]);

  const sendRecordingToBackend = useCallback(
    async (audioBlob: Blob) => {
      onVoiceProcessingChange(true);
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
          const transcribedText = res.headers.get('X-Transcribed-Text');
          if (sessionId) {
            setCurrentSessionId(parseInt(sessionId));
            setIsNewSession(false);
          }
          console.log('Transcribed:', transcribedText);
          if (res.body) {
            try {
              const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
              playbackAudioContextRef.current = audioContext;
              const sampleRate = 24000;
              const reader = res.body.getReader();
              let nextStartTime = 0;
              let chunkCount = 0;
              let playbackStarted = false;
              const bufferChunks = 1;
              const bufferedAudioBuffers: AudioBuffer[] = [];
              let pendingBytes = new Uint8Array(0);

              const createAudioBuffer = (pcmData: Uint8Array): AudioBuffer | null => {
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
                    const audioBuffer = createAudioBuffer(pcmData);
                    if (audioBuffer) scheduleAudioBuffer(audioBuffer);
                  }

                  if (audioSourcesRef.current.length > 0) {
                    const lastScheduledEndTime = nextStartTime;
                    const now = audioContext.currentTime;
                    const timeUntilLastEnds = Math.max(0, lastScheduledEndTime - now);

                    const lastSource = audioSourcesRef.current[audioSourcesRef.current.length - 1];
                    lastSource.onended = () => {
                      onVoiceProcessingChange(false);
                    };

                    setTimeout(() => {
                      onVoiceProcessingChange(false);
                    }, (timeUntilLastEnds * 1000) + 100);
                  } else {
                    onVoiceProcessingChange(false);
                  }
                  break;
                }
                if (value?.length) {
                  const newBuffer = new Uint8Array(pendingBytes.length + value.length);
                  newBuffer.set(pendingBytes);
                  newBuffer.set(value, pendingBytes.length);
                  pendingBytes = newBuffer;
                  for (const pcmData of processBuffer()) {
                    const audioBuffer = createAudioBuffer(pcmData);
                    if (!audioBuffer) continue;
                    if (!playbackStarted) {
                      bufferedAudioBuffers.push(audioBuffer);
                      if (bufferedAudioBuffers.length >= bufferChunks) {
                        playbackStarted = true;
                        nextStartTime = audioContext.currentTime + 0.05;
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
              onVoiceProcessingChange(false);
            }
          }
        } else {
          onVoiceProcessingChange(false);
        }
      } catch (e) {
        if ((e as Error)?.name !== 'AbortError') {
          console.error('Voice processing error:', e);
        }
        onVoiceProcessingChange(false);
      }
    },
    [token, currentSessionId, isNewSession, setCurrentSessionId, setIsNewSession, onVoiceProcessingChange]
  );

  useEffect(() => {
    if (!enabled) {
      // Stop any ongoing recording
      if (mediaRecorderRef.current && isRecordingRef.current) {
        mediaRecorderRef.current.stop();
        mediaRecorderRef.current = null;
        isRecordingRef.current = false;
      }
      // Cleanup any existing audio graph when disabled
      if (processorRef.current) {
        processorRef.current.disconnect();
        processorRef.current.onaudioprocess = null;
        processorRef.current = null;
      }
      if (vadAudioContextRef.current) {
        vadAudioContextRef.current.close().catch(() => {
          /* ignore */
        });
        vadAudioContextRef.current = null;
      }
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((t) => t.stop());
        mediaStreamRef.current = null;
      }
      recordingChunksRef.current = [];
      return;
    }

    if (
      !window.isSecureContext &&
      window.location.hostname !== 'localhost' &&
      window.location.hostname !== '127.0.0.1'
    ) {
      alert(
        'Microphone access blocked for Open Mic: You are accessing this site via an insecure connection (HTTP). Browsers require HTTPS for microphone access on mobile devices. Please use HTTPS or localhost.'
      );
      return;
    }

    let cancelled = false;

    const setup = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }

        const AudioCtx = (window.AudioContext || (window as any).webkitAudioContext) as typeof AudioContext;
        const vadAudioContext = new AudioCtx();
        const source = vadAudioContext.createMediaStreamSource(stream);
        const processor = vadAudioContext.createScriptProcessor(2048, 1, 1);

        vadAudioContextRef.current = vadAudioContext;
        mediaStreamRef.current = stream;
        processorRef.current = processor;

        const energyThreshold = 0.02; // tweakable; ~ -34 dBFS
        const minConsecutiveBuffers = 3; // require several loud buffers to avoid transient noise
        const minSilenceBuffers = 10; // require silence for this many buffers before stopping recording
        let aboveThresholdCount = 0;
        let belowThresholdCount = 0;
        let hasStartedRecording = false;

        processor.onaudioprocess = (event: AudioProcessingEvent) => {
          const input = event.inputBuffer.getChannelData(0);
          let sumSquares = 0;
          for (let i = 0; i < input.length; i++) {
            const sample = input[i];
            sumSquares += sample * sample;
          }
          const rms = Math.sqrt(sumSquares / input.length);

          if (rms >= energyThreshold) {
            aboveThresholdCount += 1;
            belowThresholdCount = 0;

            // Start recording if speech detected and not already recording
            if (!isRecordingRef.current && aboveThresholdCount >= minConsecutiveBuffers) {
              // Interrupt any ongoing playback (both from regular recording and open mic)
              onInterruptPlayback();
              stopPlayback();
              // Start recording
              try {
                const mediaRecorder = new MediaRecorder(stream);
                mediaRecorderRef.current = mediaRecorder;
                recordingChunksRef.current = [];
                mediaRecorder.ondataavailable = (e) => {
                  if (e.data.size > 0) recordingChunksRef.current.push(e.data);
                };
                mediaRecorder.onstop = async () => {
                  if (recordingChunksRef.current.length > 0) {
                    const audioBlob = new Blob(recordingChunksRef.current, { type: 'audio/wav' });
                    await sendRecordingToBackend(audioBlob);
                  }
                  recordingChunksRef.current = [];
                  isRecordingRef.current = false;
                  hasStartedRecording = false;
                };
                mediaRecorder.start();
                isRecordingRef.current = true;
                hasStartedRecording = true;
              } catch (err) {
                console.error('Error starting MediaRecorder:', err);
              }
            }
          } else {
            aboveThresholdCount = 0;
            // If we're recording and detect silence, count it
            if (isRecordingRef.current && hasStartedRecording) {
              belowThresholdCount += 1;
              // Stop recording after sufficient silence
              if (belowThresholdCount >= minSilenceBuffers && mediaRecorderRef.current) {
                mediaRecorderRef.current.stop();
                mediaRecorderRef.current = null;
                belowThresholdCount = 0;
              }
            }
          }
        };

        source.connect(processor);
        processor.connect(vadAudioContext.destination);
      } catch (err) {
        console.error('Error setting up Open Mic interruption:', err);
      }
    };

    setup();

    return () => {
      cancelled = true;
      // Stop any ongoing recording
      if (mediaRecorderRef.current && isRecordingRef.current) {
        mediaRecorderRef.current.stop();
        mediaRecorderRef.current = null;
        isRecordingRef.current = false;
      }
      if (processorRef.current) {
        processorRef.current.disconnect();
        processorRef.current.onaudioprocess = null;
        processorRef.current = null;
      }
      if (vadAudioContextRef.current) {
        vadAudioContextRef.current.close().catch(() => {
          /* ignore */
        });
        vadAudioContextRef.current = null;
      }
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((t) => t.stop());
        mediaStreamRef.current = null;
      }
      recordingChunksRef.current = [];
    };
  }, [
    enabled,
    onInterruptPlayback,
    sendRecordingToBackend,
    token,
    currentSessionId,
    isNewSession,
    setCurrentSessionId,
    setIsNewSession,
    onVoiceProcessingChange,
  ]);
}

