'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import type { VoiceServerMessage, ModuleProgress } from '@/types/interview';

interface UseVoiceOptions {
  sessionId: string;
  onNextQuestion?: (data: {
    question_id: string | null;
    question_text: string | null;
    question_type: string | null;
    module_progress: ModuleProgress;
    status: string;
    module_summary?: string;
  }) => void;
  onError?: (message: string) => void;
}

interface UseVoiceReturn {
  isRecording: boolean;
  isConnected: boolean;
  finalTranscript: string;
  isProcessing: boolean;
  error: string | null;
  timeoutMessage: string | null;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  switchToText: () => void;
  disconnect: () => void;
  clearTranscript: () => void;
}

/**
 * Custom hook for voice WebSocket + manual push-to-talk recording.
 *
 * User taps mic to start recording, taps stop to end.
 * On stop, the accumulated PCM audio is sent as one binary frame
 * to the backend for Whisper transcription.
 */
export function useVoice({
  sessionId,
  onNextQuestion,
  onError,
}: UseVoiceOptions): UseVoiceReturn {
  const [isRecording, setIsRecording] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [finalTranscript, setFinalTranscript] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [timeoutMessage, setTimeoutMessage] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  // Accumulate PCM chunks while recording
  const chunksRef = useRef<Int16Array[]>([]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanupAudio();
      cleanupWebSocket();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const cleanupAudio = useCallback(() => {
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    chunksRef.current = [];
  }, []);

  const cleanupWebSocket = useCallback(() => {
    if (wsRef.current) {
      if (wsRef.current.readyState === WebSocket.OPEN) {
        try {
          wsRef.current.send(JSON.stringify({ type: 'control', action: 'stop' }));
        } catch {
          // ignore
        }
      }
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  const connectWebSocket = useCallback((): Promise<WebSocket> => {
    return new Promise((resolve, reject) => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = process.env.NEXT_PUBLIC_API_URL
        ? new URL(process.env.NEXT_PUBLIC_API_URL).host
        : 'localhost:8000';
      const url = `${protocol}//${host}/api/v1/voice/${sessionId}`;

      const ws = new WebSocket(url);
      ws.binaryType = 'arraybuffer';

      ws.onopen = () => {
        setIsConnected(true);
        setError(null);
        resolve(ws);
      };

      ws.onmessage = (event) => {
        try {
          const msg: VoiceServerMessage = JSON.parse(event.data);
          handleServerMessage(msg);
        } catch {
          // Non-JSON message, ignore
        }
      };

      ws.onerror = () => {
        setError('WebSocket connection error');
        reject(new Error('WebSocket connection failed'));
      };

      ws.onclose = () => {
        setIsConnected(false);
        setIsRecording(false);
      };

      wsRef.current = ws;
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  const handleServerMessage = useCallback(
    (msg: VoiceServerMessage) => {
      switch (msg.type) {
        case 'final_transcript':
          setFinalTranscript(msg.text);
          setIsProcessing(false);
          break;

        case 'processing':
          setIsProcessing(true);
          break;

        case 'next_question':
          setIsProcessing(false);
          setFinalTranscript('');
          setTimeoutMessage(null);
          setIsRecording(false);
          onNextQuestion?.(msg);
          break;

        case 'error':
          setIsProcessing(false);
          setIsRecording(false);
          setError(msg.message);
          onError?.(msg.message);
          break;

        case 'timeout_prompt':
          setTimeoutMessage(msg.message);
          break;
      }
    },
    [onNextQuestion, onError]
  );

  const startRecording = useCallback(async () => {
    setError(null);
    setTimeoutMessage(null);
    setFinalTranscript('');
    chunksRef.current = [];

    try {
      // Connect WebSocket if not connected
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        await connectWebSocket();
      }

      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      streamRef.current = stream;

      // Create AudioContext — use device's native sample rate, we'll resample later
      const audioContext = new AudioContext();
      audioContextRef.current = audioContext;
      const nativeSampleRate = audioContext.sampleRate;

      const source = audioContext.createMediaStreamSource(stream);

      // Capture PCM chunks and resample to 16kHz for Whisper
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (event) => {
        const float32 = event.inputBuffer.getChannelData(0);
        // Resample from native rate to 16kHz
        const ratio = nativeSampleRate / 16000;
        const outLength = Math.floor(float32.length / ratio);
        const pcm16 = new Int16Array(outLength);
        for (let i = 0; i < outLength; i++) {
          const srcIndex = Math.floor(i * ratio);
          const s = Math.max(-1, Math.min(1, float32[srcIndex]));
          pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }
        chunksRef.current.push(pcm16);
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      setIsRecording(true);

      // Send start control message
      wsRef.current?.send(JSON.stringify({ type: 'control', action: 'start' }));
    } catch (err) {
      const message =
        err instanceof DOMException && err.name === 'NotAllowedError'
          ? 'Microphone access denied. Please allow microphone access and try again.'
          : 'Failed to start recording. Please check your microphone.';
      setError(message);
      onError?.(message);
      cleanupAudio();
    }
  }, [connectWebSocket, cleanupAudio, onError]);

  const stopRecording = useCallback(() => {
    if (!isRecording) return;

    // Concatenate all PCM chunks into one buffer
    const chunks = chunksRef.current;
    const totalLength = chunks.reduce((sum, c) => sum + c.length, 0);

    // Stop audio capture first
    cleanupAudio();
    setIsRecording(false);

    // Skip if too short (< 0.5s at 16kHz = 8000 samples)
    if (totalLength < 8000) {
      setError('Recording too short. Please speak for longer.');
      return;
    }

    // Merge chunks and send as one binary frame
    const merged = new Int16Array(totalLength);
    let offset = 0;
    for (const chunk of chunks) {
      merged.set(chunk, offset);
      offset += chunk.length;
    }

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(merged.buffer);
      setIsProcessing(true);
    }
  }, [isRecording, cleanupAudio]);

  const switchToText = useCallback(() => {
    cleanupAudio();
    setIsRecording(false);

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'control', action: 'switch_to_text' }));
    }

    cleanupWebSocket();
  }, [cleanupAudio, cleanupWebSocket]);

  const clearTranscript = useCallback(() => {
    setFinalTranscript('');
  }, []);

  const disconnect = useCallback(() => {
    cleanupAudio();
    cleanupWebSocket();
    setIsRecording(false);
    setFinalTranscript('');
    setIsProcessing(false);
  }, [cleanupAudio, cleanupWebSocket]);

  return {
    isRecording,
    isConnected,
    finalTranscript,
    isProcessing,
    error,
    timeoutMessage,
    startRecording,
    stopRecording,
    switchToText,
    disconnect,
    clearTranscript,
  };
}
