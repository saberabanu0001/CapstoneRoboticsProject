import { Image } from 'expo-image';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { Audio } from 'expo-av';
import * as FileSystem from 'expo-file-system/legacy';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRouter } from 'expo-router';
import { useIsFocused } from '@react-navigation/native';
import Animated, { 
  FadeInDown, 
  FadeIn,
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withSequence,
  withTiming
} from 'react-native-reanimated';

import { CameraVideo } from '@/components/camera-video';
import { RobotEyes } from '@/components/robot-eyes-svg';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { IconSymbol } from '@/components/ui/icon-symbol';
import { useRobot } from '@/context/robot-provider';
import { DEFAULT_CLOUD_URL } from '@/services/cloud-api';

interface VoiceLogEntry {
  id: string;
  label: string;
  message: string;
  tone: 'info' | 'partial' | 'final' | 'client' | 'error';
  timestamp: Date;
}

const MAX_LOG_ITEMS = 50;
const AUDIO_SAMPLE_RATE = 16000;

const buildWebSocketUrl = (baseUrl: string | undefined, path: string) => {
  if (!baseUrl) return undefined;

  try {
    const normalizedUrl = baseUrl.startsWith('http') ? baseUrl : `http://${baseUrl}`;
    const parsedUrl = new URL(normalizedUrl);
    const host = parsedUrl.hostname;
    const isIp = /^\d{1,3}(\.\d{1,3}){3}$/.test(host) || host === 'localhost';

    parsedUrl.protocol = isIp
      ? 'ws:'
      : parsedUrl.protocol === 'https:'
        ? 'wss:'
        : 'ws:';

    parsedUrl.pathname = `${parsedUrl.pathname.replace(/\/$/, '')}${path}`;
    parsedUrl.search = '';

    return parsedUrl.toString();
  } catch (error) {
    console.warn('Invalid base URL for WebSocket', error);
    return undefined;
  }
};

export default function AgenticVoiceScreen() {
  const router = useRouter();
  const { baseUrl, status } = useRobot();
  const isFocused = useIsFocused();

  const cameraWsUrl = useMemo(() => buildWebSocketUrl(baseUrl, '/camera/ws'), [baseUrl]);
  // Audio goes to PC cloud server, not Pi
  const audioWsUrl = useMemo(() => buildWebSocketUrl(DEFAULT_CLOUD_URL, '/voice'), []);

  const cameraSocket = useRef<WebSocket | null>(null);
  const audioSocket = useRef<WebSocket | null>(null);
  const recordingRef = useRef<Audio.Recording | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [currentFrame, setCurrentFrame] = useState<string | null>(null);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [audioError, setAudioError] = useState<string | null>(null);
  const [isCameraStreaming, setIsCameraStreaming] = useState(false);
  const [isCameraConnecting, setIsCameraConnecting] = useState(false);
  const [isAudioConnected, setIsAudioConnected] = useState(false);
  const [isAudioConnecting, setIsAudioConnecting] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingError, setRecordingError] = useState<string | null>(null);
  const [voiceLog, setVoiceLog] = useState<VoiceLogEntry[]>([]);
  const [detectedGesture, setDetectedGesture] = useState<'like' | 'heart' | 'none'>('none');
  const lastProcessedGestureRef = useRef<'like' | 'heart' | 'none'>('none');
  const gestureTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  
  // Gesture detection will come from robot via WebSocket or status updates

  // Animation for recording pulse
  const recordingPulse = useSharedValue(1);

  // Determine robot emotion based on voice control state and gestures
  const getEmotion = () => {
    // Gesture-based emotions take priority
    if (detectedGesture === 'heart') return 'love'; // Heart gesture → heart eyes
    if (detectedGesture === 'like') return 'happy'; // Like gesture → happy
    
    // Fall back to state-based emotions
    if (isRecording) return 'curious'; // Active listening
    if (!isAudioConnected && !isCameraStreaming) return 'neutral'; // Not connected
    if (isAudioConnected && isCameraStreaming) return 'happy'; // Fully connected
    return 'thinking'; // Partially connected
  };

  // Handle gesture detection from robot (sent via status updates)
  // Gestures stay active for 5 seconds after detection
  const handleGestureDetected = useCallback((gesture: 'like' | 'heart' | 'none') => {
    // Only update if gesture actually changed
    if (lastProcessedGestureRef.current === gesture) {
      return; // No change, skip update
    }
    
    // Clear existing timeout when gesture changes
    if (gestureTimeoutRef.current) {
      clearTimeout(gestureTimeoutRef.current);
      gestureTimeoutRef.current = null;
    }
    
    // If a gesture (heart/like) is detected, set it and keep it for 5 seconds
    if (gesture !== 'none') {
      // Update ref and state
      lastProcessedGestureRef.current = gesture;
      setDetectedGesture(gesture);
      console.log(`[Gesture] Changed to: ${gesture}`);
      
      // Set timeout to reset after 5 seconds
      gestureTimeoutRef.current = setTimeout(() => {
        // Only reset if gesture is still the same (hasn't changed)
        if (lastProcessedGestureRef.current === gesture) {
          setDetectedGesture('none');
          lastProcessedGestureRef.current = 'none';
          gestureTimeoutRef.current = null;
          console.log('[Gesture] Reset to: none (after 5 seconds)');
        }
      }, 5000); // 5 seconds
    } else {
      // When 'none' is detected, only update if no gesture is currently active
      // This prevents 'none' from interrupting an active gesture timer
      if (lastProcessedGestureRef.current === 'none') {
        return; // Already 'none', no need to update
      }
      // If a gesture is active, the timeout will handle the reset
      // Don't immediately change to 'none' - let the timer expire
    }
  }, []); // No dependencies - uses refs which don't change

  const isOnline = Boolean(status?.network?.ip);
  
  // Listen for gesture updates from robot status (robot detects gestures from OAK-D camera)
  useEffect(() => {
    const gesture = status?.telemetry?.gesture ?? status?.gesture;
    if (gesture && gesture !== detectedGesture) {
      handleGestureDetected(gesture as 'like' | 'heart' | 'none');
    }
  }, [status?.telemetry?.gesture, status?.gesture, detectedGesture, handleGestureDetected]);

  useEffect(() => {
    if (isRecording) {
      recordingPulse.value = withRepeat(
        withSequence(
          withTiming(1.1, { duration: 500 }),
          withTiming(1, { duration: 500 })
        ),
        -1,
        false
      );
    } else {
      recordingPulse.value = withTiming(1, { duration: 200 });
    }
  }, [isRecording]);

  const recordingPulseStyle = useAnimatedStyle(() => ({
    transform: [{ scale: recordingPulse.value }],
  }));

  const appendLog = useCallback((entry: Omit<VoiceLogEntry, 'id' | 'timestamp'>) => {
    setVoiceLog((prev) => {
      const next = [
        {
          id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
          timestamp: new Date(),
          ...entry,
        },
        ...prev,
      ];

      return next.slice(0, MAX_LOG_ITEMS);
    });
  }, []);

  const connectCamera = useCallback(() => {
    if (!cameraWsUrl) {
      setCameraError('No camera WebSocket URL available');
      return;
    }

    // Don't connect if already connected or connecting
    if (cameraSocket.current?.readyState === WebSocket.OPEN) {
      setIsCameraStreaming(true);
      setIsCameraConnecting(false);
      return;
    }

    if (cameraSocket.current?.readyState === WebSocket.CONNECTING) {
      return; // Already connecting
    }

    // Close existing connection if any
    if (cameraSocket.current) {
      cameraSocket.current.close();
      cameraSocket.current = null;
    }

    setIsCameraConnecting(true);
    setCameraError(null);

    const ws = new WebSocket(cameraWsUrl);
    cameraSocket.current = ws;

    ws.onopen = () => {
      setIsCameraConnecting(false);
      setIsCameraStreaming(true);
      setCameraError(null);
      // Clear any pending reconnect timeout
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.error) {
          setCameraError(data.error);
          return;
        }

        if (data.frame) {
          setCurrentFrame(`data:image/jpeg;base64,${data.frame}`);
        }

        // Extract gesture data from camera stream (real-time updates)
        // Only update when gesture actually changes to prevent animation flicker
        if (data.gesture !== undefined) {
          const gesture = data.gesture as 'like' | 'heart' | 'none';
          const confidence = data.gesture_confidence ?? 0;
          // Only process if confidence is above threshold
          if (gesture === 'none' || confidence > 0.5) {
            // handleGestureDetected will check if gesture changed internally
            handleGestureDetected(gesture);
          }
        }
      } catch (error) {
        console.warn('Camera stream parse error', error);
      }
    };

    ws.onerror = () => {
      setCameraError('Camera stream error');
      setIsCameraConnecting(false);
      setIsCameraStreaming(false);
    };

    ws.onclose = () => {
      setIsCameraStreaming(false);
      setIsCameraConnecting(false);
      
      // Auto-reconnect if screen is still focused and we have a URL
      if (isFocused && cameraWsUrl && cameraSocket.current === ws) {
        // Clear any existing timeout
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
        }
        // Reconnect after a short delay
        reconnectTimeoutRef.current = setTimeout(() => {
          if (isFocused && cameraWsUrl) {
            connectCamera();
          }
        }, 1000);
      }
    };
  }, [cameraWsUrl, isFocused, handleGestureDetected]);

  const disconnectCamera = useCallback(() => {
    // Clear any pending reconnect
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (cameraSocket.current) {
      cameraSocket.current.close();
      cameraSocket.current = null;
    }
    setIsCameraStreaming(false);
    setIsCameraConnecting(false);
    setCurrentFrame(null);
  }, []);

  const handleToggleCamera = useCallback(() => {
    if (isCameraStreaming || isCameraConnecting) {
      disconnectCamera();
    } else {
      connectCamera();
    }
  }, [connectCamera, disconnectCamera, isCameraConnecting, isCameraStreaming]);

  // Connect camera when screen is focused
  useEffect(() => {
    if (isFocused && cameraWsUrl) {
      // Check if we need to reconnect
      const socket = cameraSocket.current;
      if (!socket || socket.readyState === WebSocket.CLOSED || socket.readyState === WebSocket.CLOSING) {
        // Connection is closed, reconnect
        if (!isCameraStreaming && !isCameraConnecting) {
          connectCamera();
        }
      } else if (socket.readyState === WebSocket.OPEN) {
        // Connection is open, just update state
        setIsCameraStreaming(true);
        setIsCameraConnecting(false);
      }
      // If CONNECTING, just wait
    }
  }, [isFocused, cameraWsUrl, connectCamera, isCameraStreaming, isCameraConnecting]);

  // Only disconnect on actual component unmount (not just blur)
  useEffect(() => {
    return () => {
      // Cleanup on unmount
      disconnectCamera();
    };
  }, [disconnectCamera]);

  const connectAudioSocket = useCallback(() => {
    if (!audioWsUrl) {
      setAudioError('No audio WebSocket URL available');
      return;
    }

    setIsAudioConnecting(true);
    setAudioError(null);

    const ws = new WebSocket(audioWsUrl);
    audioSocket.current = ws;

    ws.onopen = () => {
      setIsAudioConnecting(false);
      setIsAudioConnected(true);
      appendLog({ label: 'Voice link ready', message: 'Connected to cloud AI server for voice processing.', tone: 'info' });
    };

    ws.onmessage = (event) => {
      try {
        const data = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;

        // Handle test responses
        if (data.type === 'status') {
          appendLog({ label: 'Robot', message: data.message, tone: 'info' });
          return;
        }

        if (data.type === 'chunk_received') {
          // Silent acknowledgment, don't spam logs
          return;
        }

        if (data.type === 'audio_complete') {
          appendLog({
            label: 'Robot',
            message: `Received ${data.total_chunks} audio chunks successfully`,
            tone: 'info'
          });
          return;
        }

        // Handle transcription responses (for future)
        if (data.finalTranscript || data.text) {
          appendLog({
            label: 'Transcript',
            message: data.finalTranscript || data.text,
            tone: 'final'
          });
          return;
        }

        if (data.partialTranscript) {
          appendLog({ label: 'Partial', message: data.partialTranscript, tone: 'partial' });
          return;
        }

        if (data.assistant) {
          appendLog({ label: 'Assistant', message: data.assistant, tone: 'info' });
          return;
        }

        if (data.message) {
          appendLog({ label: 'Robot', message: data.message, tone: 'info' });
          return;
        }

        // Fallback for unknown messages
        if (data.type) {
          appendLog({
            label: 'Robot',
            message: `Received: ${data.type}`,
            tone: 'info'
          });
        }
      } catch (error) {
        console.warn('Audio WebSocket message parse error', error);
        appendLog({ label: 'Robot', message: String(event.data ?? 'Message received'), tone: 'info' });
      }
    };

    ws.onerror = (error) => {
      console.warn('Audio WebSocket error', error);
      setAudioError('Audio stream error');
      setIsAudioConnecting(false);
      setIsAudioConnected(false);
    };

    ws.onclose = () => {
      setIsAudioConnected(false);
      setIsAudioConnecting(false);
      appendLog({ label: 'Voice link closed', message: 'Cloud AI server disconnected.', tone: 'error' });
    };
  }, [appendLog, audioWsUrl]);

  const disconnectAudioSocket = useCallback(() => {
    if (audioSocket.current) {
      audioSocket.current.close();
      audioSocket.current = null;
    }
    setIsAudioConnected(false);
    setIsAudioConnecting(false);
  }, []);

  useEffect(() => {
    if (audioWsUrl && !isAudioConnected && !isAudioConnecting) {
      connectAudioSocket();
    }
  }, [audioWsUrl, connectAudioSocket, isAudioConnected, isAudioConnecting]);

  useEffect(() => () => disconnectAudioSocket(), [disconnectAudioSocket]);

  const sendAudioChunks = useCallback(async (base64Payload: string) => {
    if (!audioSocket.current || audioSocket.current.readyState !== WebSocket.OPEN) {
      setRecordingError('Audio socket not connected');
      appendLog({ label: 'Error', message: 'Audio socket not connected', tone: 'error' });
      return;
    }

    try {
      const chunkSize = 8000;
      let chunksSent = 0;

      for (let i = 0; i < base64Payload.length; i += chunkSize) {
        const chunk = base64Payload.slice(i, i + chunkSize);
        audioSocket.current.send(
          JSON.stringify({ type: 'audio_chunk', encoding: 'base64', data: chunk })
        );
        chunksSent++;
      }

      audioSocket.current.send(
        JSON.stringify({ type: 'audio_end', encoding: 'base64', sampleRate: AUDIO_SAMPLE_RATE })
      );

      appendLog({
        label: 'You',
        message: `Sent ${chunksSent} audio chunks to robot`,
        tone: 'client'
      });
    } catch (error) {
      console.error('Failed to send audio chunks', error);
      appendLog({ label: 'Error', message: 'Failed to send audio to robot', tone: 'error' });
      setRecordingError('Failed to send audio');
    }
  }, [appendLog]);

  const stopRecording = useCallback(async () => {
    if (!recordingRef.current) {
      return;
    }

    try {
      await recordingRef.current.stopAndUnloadAsync();
      const uri = recordingRef.current.getURI();
      recordingRef.current = null;
      setIsRecording(false);

      if (!uri) {
        throw new Error('No recording URI available');
      }

      // Read as base64 - use string literal, not enum
      const base64 = await FileSystem.readAsStringAsync(uri, {
        encoding: FileSystem.EncodingType.Base64,
      });

      if (!base64) {
        throw new Error('Failed to read audio file');
      }

      await sendAudioChunks(base64);

      // Clean up the file
      try {
        await FileSystem.deleteAsync(uri, { idempotent: true });
      } catch (deleteError) {
        console.warn('Failed to delete recording file', deleteError);
      }
    } catch (error) {
      console.error('Failed to stop recording', error);
      setRecordingError('Failed to process recording');
      appendLog({
        label: 'Error',
        message: `Recording error: ${error instanceof Error ? error.message : 'Unknown error'}`,
        tone: 'error'
      });
    } finally {
      recordingRef.current = null;
      try {
        await Audio.setAudioModeAsync({
          allowsRecordingIOS: false,
          playsInSilentModeIOS: false,
        });
      } catch (audioModeError) {
        console.warn('Failed to reset audio mode', audioModeError);
      }
    }
  }, [sendAudioChunks, appendLog]);

  const startRecording = useCallback(async () => {
    if (isRecording || isAudioConnecting) {
      return;
    }

    if (!isAudioConnected) {
      setRecordingError('Audio connection required');
      return;
    }

    setRecordingError(null);

    try {
      // Request permission
      const permission = await Audio.requestPermissionsAsync();
      if (permission.status !== 'granted') {
        setRecordingError('Microphone permission required');
        appendLog({
          label: 'Error',
          message: 'Microphone permission is required to talk to the robot',
          tone: 'error'
        });
        return;
      }

      // Set audio mode - critical for iOS
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
        staysActiveInBackground: false, // Changed to false to avoid iOS conflict
        shouldDuckAndroid: true,
        playThroughEarpieceAndroid: false,
      });

      // Prepare recording
      const recording = new Audio.Recording();

      // Platform-specific recording options
      const recordingOptions = {
        android: {
          extension: '.wav',
          outputFormat: Audio.AndroidOutputFormat.DEFAULT,
          audioEncoder: Audio.AndroidAudioEncoder.DEFAULT,
          sampleRate: AUDIO_SAMPLE_RATE,
          numberOfChannels: 1,
          bitRate: 128000,
        },
        ios: {
          extension: '.wav',
          audioQuality: Audio.IOSAudioQuality.HIGH,
          sampleRate: AUDIO_SAMPLE_RATE,
          numberOfChannels: 1,
          bitRate: 128000,
          linearPCMBitDepth: 16,
          linearPCMIsBigEndian: false,
          linearPCMIsFloat: false,
        },
        web: {
          mimeType: 'audio/wav',
          bitsPerSecond: 128000,
        },
      };

      await recording.prepareToRecordAsync(recordingOptions);
      await recording.startAsync();

      recordingRef.current = recording;
      setIsRecording(true);

      appendLog({
        label: 'You',
        message: 'Recording... release to send',
        tone: 'client'
      });
    } catch (error) {
      console.error('Failed to start recording', error);

      let errorMessage = 'Unable to start recording';
      if (error instanceof Error) {
        if (error.message.includes('background')) {
          errorMessage = 'Cannot record while app is in background';
        } else if (error.message.includes('permission')) {
          errorMessage = 'Microphone permission denied';
        } else {
          errorMessage = error.message;
        }
      }

      setRecordingError(errorMessage);
      appendLog({
        label: 'Error',
        message: errorMessage,
        tone: 'error'
      });

      // Clean up
      recordingRef.current = null;
      try {
        await Audio.setAudioModeAsync({ allowsRecordingIOS: false });
      } catch (cleanupError) {
        console.warn('Failed to reset audio mode after error', cleanupError);
      }
    }
  }, [appendLog, isAudioConnecting, isAudioConnected, isRecording]);

  // Cleanup gesture timeout on unmount
  useEffect(() => {
    return () => {
      if (gestureTimeoutRef.current) {
        clearTimeout(gestureTimeoutRef.current);
        gestureTimeoutRef.current = null;
      }
    };
  }, []);

  return (
    <SafeAreaView style={styles.safeArea} edges={["top", "bottom"]}>
      <ThemedView style={styles.container}>
        <Animated.View 
          entering={FadeIn.duration(400)}
          style={styles.headerRow}
        >
          <Pressable style={styles.backButton} onPress={() => router.back()}>
            <IconSymbol name="chevron.left" size={16} color="#E5E7EB" />
          </Pressable>
          <ThemedText type="title">Voice Control</ThemedText>
        </Animated.View>

        {/* Full Width Robot Eyes with Reduced Height */}
        <Animated.View entering={FadeIn.delay(50).duration(600)} style={styles.fullWidthEyesContainer}>
          <RobotEyes emotion={getEmotion()} isOnline={isOnline} />
        </Animated.View>

        {/* Status Row and Camera - No Gap */}
        <View style={styles.statusAndCameraContainer}>
          <Animated.View 
            entering={FadeInDown.delay(100).duration(400)}
            style={styles.statusRow}
          >
            <View style={styles.statusPill}>
              <View style={[styles.statusDot, isCameraStreaming ? styles.statusOn : styles.statusOff]} />
              <ThemedText style={styles.statusText}>
                Camera {isCameraStreaming ? 'streaming' : isCameraConnecting ? 'connecting' : 'idle'}
              </ThemedText>
            </View>
            <View style={styles.statusPill}>
              <View style={[styles.statusDot, isAudioConnected ? styles.statusOn : styles.statusOff]} />
              <ThemedText style={styles.statusText}>
                Voice {isAudioConnected ? 'linked' : isAudioConnecting ? 'connecting' : 'disconnected'}
              </ThemedText>
            </View>
          </Animated.View>

          <CameraVideo
            wsUrl={cameraWsUrl}
            currentFrame={currentFrame}
            isConnecting={isCameraConnecting}
            isStreaming={isCameraStreaming}
            error={cameraError}
            onToggleStream={handleToggleCamera}
            detectedGesture={detectedGesture}
          />
        </View>

        <Animated.View entering={FadeInDown.delay(200).duration(400)} style={{ flex: 1 }}>
          <ThemedView style={styles.logCard}>
            <View style={styles.logLegend}>
              <View style={[styles.legendDot, styles.legendRobot]} />
              <ThemedText style={styles.legendText}>AI</ThemedText>
              <View style={[styles.legendDot, styles.legendYou]} />
              <ThemedText style={styles.legendText}>You</ThemedText>
            </View>
            <ScrollView style={styles.logScroll} showsVerticalScrollIndicator={false}>
              {voiceLog.length === 0 ? (
                <View style={styles.emptyLog}>
                  <Image
                    source={require('@/assets/images/rovy.png')}
                    style={styles.emptyImage}
                    contentFit="contain"
                  />
                  <ThemedText style={styles.emptyTitle}>Ready to chat</ThemedText>
                  <ThemedText style={styles.emptyText}>
                    Hold the microphone button to start talking with JARVIS
                  </ThemedText>
                </View>
              ) : (
                voiceLog.map((entry, index) => (
                  <Animated.View
                    key={entry.id}
                    entering={FadeInDown.delay(index * 30).duration(300)}
                  >
                    <View
                      style={[
                        styles.logItem,
                        entry.tone === 'client' ? styles.logItemClient : styles.logItemRobot,
                      ]}
                    >
                      <View style={styles.logItemHeader}>
                        <ThemedText style={styles.logLabel}>{entry.label}</ThemedText>
                        <ThemedText style={styles.logTime}>
                          {entry.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                        </ThemedText>
                      </View>
                      <ThemedText style={styles.logMessage}>{entry.message}</ThemedText>
                    </View>
                  </Animated.View>
                ))
              )}
            </ScrollView>
          </ThemedView>
        </Animated.View>

        <Animated.View entering={FadeInDown.delay(300).duration(400)}>
          <ThemedView style={styles.card}>
            <View style={styles.cardHeader}>
              <ThemedText type="subtitle">Push-to-talk</ThemedText>
              <Pressable onPress={isAudioConnected ? disconnectAudioSocket : connectAudioSocket}>
                <ThemedText type="link">{isAudioConnected ? 'Reconnect' : 'Retry link'}</ThemedText>
              </Pressable>
            </View>
            <Animated.View style={isRecording ? recordingPulseStyle : undefined}>
              <Pressable
                style={[
                  styles.talkButton,
                  isRecording && styles.talkButtonActive,
                  !isAudioConnected && styles.talkButtonDisabled,
                ]}
                onPressIn={startRecording}
                onPressOut={stopRecording}
                disabled={!isAudioConnected}
              >
                {isRecording ? (
                  <>
                    <View style={styles.recordingIndicator}>
                      <View style={styles.recordingDot} />
                    </View>
                    <ThemedText style={styles.talkButtonText}>Listening...</ThemedText>
                  </>
                ) : (
                  <>
                    <IconSymbol name="mic.fill" size={18} color="#04110B" />
                    <ThemedText style={styles.talkButtonText}>
                      {!isAudioConnected ? 'Waiting for connection...' : 'Hold to talk'}
                    </ThemedText>
                  </>
                )}
              </Pressable>
            </Animated.View>
            {recordingError ? (
              <ThemedText style={styles.errorText}>{recordingError}</ThemedText>
            ) : null}
            {audioError ? (
              <ThemedText style={styles.errorText}>{audioError}</ThemedText>
            ) : null}
          </ThemedView>
        </Animated.View>

        {/* Gesture detection runs on OAK-D camera stream frames via useEffect */}
      </ThemedView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#161616',
  },
  container: {
    flex: 1,
    padding: 24,
    gap: 16,
    backgroundColor: '#161616',
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  backButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    padding: 8,
    borderWidth: 1,
    borderColor: '#202020',
    backgroundColor: '#1C1C1C',
  },
  fullWidthEyesContainer: {
    width: '100%',
    height: 100,
    alignItems: 'center',
    justifyContent: 'center',
    marginVertical: 8,
    overflow: 'hidden',
  },
  statusAndCameraContainer: {
    gap: 0,
  },
  statusRow: {
    flexDirection: 'row',
    gap: 10,
    alignItems: 'center',
    marginBottom: 0,
  },
  statusPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 10,
    paddingVertical: 8,
    borderRadius: 30,
    backgroundColor: '#0F1512',
    borderWidth: 1,
    borderColor: '#202020',
  },
  statusDot: {
    width: 10,
    height: 10,
    borderRadius: 10,
  },
  statusOn: {
    backgroundColor: '#1DD1A1',
  },
  statusOff: {
    backgroundColor: '#4B5563',
  },
  statusText: {
    color: '#E5E7EB',
    fontSize: 13,
  },
  card: {
    padding: 16,
    gap: 12,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(37, 37, 37, 0.6)',
    backgroundColor: 'rgba(26, 26, 26, 0.7)',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 2,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  cardDescription: {
    color: '#9CA3AF',
    lineHeight: 20,
  },
  talkButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    paddingVertical: 18,
    borderRadius: 14,
    backgroundColor: '#1DD1A1',
    shadowColor: '#1DD1A1',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  talkButtonActive: {
    backgroundColor: '#EF4444',
    shadowColor: '#EF4444',
  },
  talkButtonDisabled: {
    opacity: 0.4,
  },
  talkButtonText: {
    color: '#04110B',
    fontFamily: 'JetBrainsMono_600SemiBold',
    fontSize: 15,
  },
  recordingIndicator: {
    width: 20,
    height: 20,
    borderRadius: 10,
    backgroundColor: 'rgba(4, 17, 11, 0.2)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  recordingDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#04110B',
  },
  errorText: {
    color: '#F87171',
    fontSize: 12,
  },
  logCard: {
    flex: 1,
    borderWidth: 1,
    borderColor: 'rgba(37, 37, 37, 0.6)',
    backgroundColor: 'rgba(15, 21, 18, 0.8)',
    borderRadius: 12,
    padding: 16,
    paddingTop: 12,
    gap: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 2,
  },
  logScroll: {
    flex: 1,
  },
  emptyLog: {
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    paddingVertical: 48,
  },
  emptyImage: {
    width: 120,
    height: 80,
    marginBottom: 8,
  },
  emptyTitle: {
    fontSize: 18,
    fontFamily: 'JetBrainsMono_600SemiBold',
    color: '#E5E7EB',
    marginBottom: 4,
  },
  emptyText: {
    color: '#9CA3AF',
    textAlign: 'center',
    lineHeight: 20,
    paddingHorizontal: 20,
  },
  logItem: {
    padding: 14,
    borderRadius: 12,
    gap: 8,
    marginBottom: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 1,
  },
  logItemRobot: {
    backgroundColor: 'rgba(17, 24, 39, 0.8)',
    borderWidth: 1,
    borderColor: 'rgba(31, 41, 55, 0.6)',
  },
  logItemClient: {
    backgroundColor: 'rgba(17, 38, 30, 0.8)',
    borderWidth: 1,
    borderColor: 'rgba(29, 209, 161, 0.4)',
  },
  logItemHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  logLabel: {
    color: '#E5E7EB',
    fontWeight: '700',
  },
  logTime: {
    color: '#6B7280',
    fontSize: 12,
  },
  logMessage: {
    color: '#E5E7EB',
    lineHeight: 20,
  },
  logLegend: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'flex-end',
    gap: 8,
    marginBottom: 8,
  },
  legendDot: {
    width: 10,
    height: 10,
    borderRadius: 10,
  },
  legendRobot: {
    backgroundColor: '#2563EB',
  },
  legendYou: {
    backgroundColor: '#1DD1A1',
  },
  legendText: {
    color: '#9CA3AF',
    fontSize: 12,
  },
});