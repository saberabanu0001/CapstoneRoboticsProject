import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  View,
  StyleSheet,
  Image,
  Pressable,
  Modal,
  ActivityIndicator,
  Alert,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Animated, { FadeIn, FadeOut } from 'react-native-reanimated';
import Voice from '@react-native-voice/voice';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { IconSymbol } from '@/components/ui/icon-symbol';
import { useRobot } from '@/context/robot-provider';

// Kodak printer service - we'll create a BLE printer manager
import { KodakPrinterManager } from '@/services/kodak-printer';

export default function PhotoTimeScreen() {
  const { status } = useRobot();
  const robotIp = status?.network?.ip;

  const [cameraStream, setCameraStream] = useState<string | null>(null);
  const [capturedPhoto, setCapturedPhoto] = useState<string | null>(null);
  const [isCapturing, setIsCapturing] = useState(false);
  const [isPrinting, setIsPrinting] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [printerConnected, setPrinterConnected] = useState(false);
  
  const wsRef = useRef<WebSocket | null>(null);
  const printerRef = useRef<KodakPrinterManager | null>(null);

  // Initialize Kodak printer manager
  useEffect(() => {
    if (!printerRef.current) {
      printerRef.current = new KodakPrinterManager();
    }
    
    // Try to connect to printer on mount
    connectToPrinter();
    
    return () => {
      if (printerRef.current) {
        printerRef.current.disconnect();
      }
    };
  }, []);

  // Connect to Kodak printer via Bluetooth
  const connectToPrinter = async () => {
    try {
      if (printerRef.current) {
        await printerRef.current.connect();
        setPrinterConnected(true);
      }
    } catch (error) {
      console.log('Printer not connected:', error);
      setPrinterConnected(false);
    }
  };

  // Setup camera stream WebSocket
  useEffect(() => {
    if (!robotIp) return;

    const connectWebSocket = () => {
      const ws = new WebSocket(`ws://${robotIp}:8000/camera/ws`);
      
      ws.onopen = () => {
        console.log('Camera WebSocket connected');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.frame) {
            setCameraStream(`data:image/jpeg;base64,${data.frame}`);
          }
        } catch (error) {
          console.error('Failed to parse camera frame:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      ws.onclose = () => {
        console.log('Camera WebSocket closed, reconnecting...');
        setTimeout(connectWebSocket, 2000);
      };

      wsRef.current = ws;
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [robotIp]);

  // Voice recognition setup
  useEffect(() => {
    Voice.onSpeechStart = () => setIsListening(true);
    Voice.onSpeechEnd = () => setIsListening(false);
    Voice.onSpeechResults = onSpeechResults;
    Voice.onSpeechError = (error) => {
      console.error('Speech error:', error);
      setIsListening(false);
    };

    return () => {
      Voice.destroy().then(Voice.removeAllListeners);
    };
  }, [capturedPhoto]);

  const onSpeechResults = (event: any) => {
    if (event.value && event.value.length > 0) {
      const command = event.value[0].toLowerCase();
      console.log('Voice command:', command);

      // Check for photo commands
      if (command.includes('take') && (command.includes('picture') || command.includes('photo'))) {
        handleTakePhoto();
      } else if (command.includes('print') && capturedPhoto) {
        handlePrint();
      } else if (command.includes('retake') || command.includes('take another')) {
        handleRetake();
      } else if (command.includes('cancel') || command.includes('close')) {
        handleRetake();
      }
    }
  };

  const startListening = async () => {
    try {
      await Voice.start('en-US');
      setIsListening(true);
    } catch (error) {
      console.error('Failed to start voice recognition:', error);
    }
  };

  const stopListening = async () => {
    try {
      await Voice.stop();
      setIsListening(false);
    } catch (error) {
      console.error('Failed to stop voice recognition:', error);
    }
  };

  // Capture photo from OakD camera using existing /shot endpoint
  const handleTakePhoto = async () => {
    if (!robotIp || isCapturing) return;

    setIsCapturing(true);
    try {
      // Use existing /shot endpoint which returns raw JPEG bytes
      const response = await fetch(`http://${robotIp}:8000/shot`, {
        method: 'GET',
      });

      if (response.ok) {
        // Convert blob to base64
        const blob = await response.blob();
        const reader = new FileReader();
        
        reader.onloadend = () => {
          const base64data = reader.result as string;
          setCapturedPhoto(base64data);
          setShowPreview(true);
          setIsCapturing(false);
        };
        
        reader.onerror = () => {
          Alert.alert('Error', 'Failed to process photo');
          setIsCapturing(false);
        };
        
        reader.readAsDataURL(blob);
      } else {
        Alert.alert('Error', 'Failed to capture photo');
        setIsCapturing(false);
      }
    } catch (error) {
      console.error('Failed to capture photo:', error);
      Alert.alert('Error', 'Failed to capture photo');
      setIsCapturing(false);
    }
  };

  // Print photo to Kodak printer
  const handlePrint = async () => {
    if (!capturedPhoto || isPrinting) return;

    if (!printerConnected) {
      Alert.alert(
        'Printer Not Connected',
        'The Kodak printer is not connected. Would you like to connect?',
        [
          { text: 'Cancel', style: 'cancel' },
          { text: 'Connect', onPress: connectToPrinter },
        ]
      );
      return;
    }

    setIsPrinting(true);
    try {
      // Extract base64 data from data URL
      const base64Data = capturedPhoto.replace(/^data:image\/\w+;base64,/, '');
      
      if (printerRef.current) {
        await printerRef.current.print(base64Data);
        Alert.alert('Success', 'Photo sent to printer!');
      }
    } catch (error) {
      console.error('Failed to print photo:', error);
      Alert.alert('Error', 'Failed to print photo');
    } finally {
      setIsPrinting(false);
    }
  };

  // Retake photo
  const handleRetake = () => {
    setCapturedPhoto(null);
    setShowPreview(false);
  };

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <ThemedView style={styles.screen}>
        {/* Header */}
        <View style={styles.header}>
          <ThemedText style={styles.title}>Photo Time</ThemedText>
          <View style={styles.statusRow}>
            <View style={[styles.statusDot, { backgroundColor: printerConnected ? '#34D399' : '#EF4444' }]} />
            <ThemedText style={styles.statusText}>
              {printerConnected ? 'Printer Ready' : 'Printer Offline'}
            </ThemedText>
          </View>
        </View>

        {/* Camera Stream */}
        <View style={styles.cameraContainer}>
          {cameraStream ? (
            <Image
              source={{ uri: cameraStream }}
              style={styles.cameraImage}
              resizeMode="cover"
            />
          ) : (
            <View style={styles.placeholderContainer}>
              <ActivityIndicator size="large" color="#3B82F6" />
              <ThemedText style={styles.placeholderText}>
                Connecting to camera...
              </ThemedText>
            </View>
          )}

          {/* Voice indicator overlay */}
          {isListening && (
            <Animated.View
              entering={FadeIn}
              exiting={FadeOut}
              style={styles.listeningOverlay}
            >
              <View style={styles.listeningIndicator}>
                <IconSymbol name="mic.fill" size={32} color="#FFFFFF" />
                <ThemedText style={styles.listeningText}>Listening...</ThemedText>
              </View>
            </Animated.View>
          )}
        </View>

        {/* Controls */}
        <View style={styles.controls}>
          {/* Voice Control Button */}
          <Pressable
            style={({ pressed }) => [
              styles.voiceButton,
              isListening && styles.voiceButtonActive,
              pressed && styles.buttonPressed,
            ]}
            onPress={isListening ? stopListening : startListening}
          >
            <IconSymbol
              name={isListening ? 'mic.fill' : 'mic'}
              size={28}
              color="#FFFFFF"
            />
            <ThemedText style={styles.buttonText}>
              {isListening ? 'Stop' : 'Voice'}
            </ThemedText>
          </Pressable>

          {/* Capture Button */}
          <Pressable
            style={({ pressed }) => [
              styles.captureButton,
              pressed && styles.buttonPressed,
              isCapturing && styles.buttonDisabled,
            ]}
            onPress={handleTakePhoto}
            disabled={isCapturing}
          >
            {isCapturing ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <>
                <IconSymbol name="camera.fill" size={32} color="#FFFFFF" />
                <ThemedText style={styles.captureButtonText}>Take Photo</ThemedText>
              </>
            )}
          </Pressable>

          {/* Connect Printer Button */}
          <Pressable
            style={({ pressed }) => [
              styles.printerButton,
              pressed && styles.buttonPressed,
            ]}
            onPress={connectToPrinter}
          >
            <IconSymbol
              name="printer.fill"
              size={28}
              color={printerConnected ? '#34D399' : '#9CA3AF'}
            />
            <ThemedText style={styles.buttonText}>Printer</ThemedText>
          </Pressable>
        </View>

        {/* Voice Commands Help */}
        <View style={styles.helpSection}>
          <ThemedText style={styles.helpTitle}>Voice Commands:</ThemedText>
          <ThemedText style={styles.helpText}>
            "Take picture" • "Print" • "Retake" • "Cancel"
          </ThemedText>
        </View>

        {/* Preview Modal */}
        <Modal
          visible={showPreview}
          transparent
          animationType="fade"
          onRequestClose={handleRetake}
        >
          <View style={styles.modalOverlay}>
            <View style={styles.previewContainer}>
              <ThemedText style={styles.previewTitle}>Photo Preview</ThemedText>
              
              {capturedPhoto && (
                <Image
                  source={{ uri: capturedPhoto }}
                  style={styles.previewImage}
                  resizeMode="contain"
                />
              )}

              <View style={styles.previewActions}>
                <Pressable
                  style={({ pressed }) => [
                    styles.previewButton,
                    styles.retakeButton,
                    pressed && styles.buttonPressed,
                  ]}
                  onPress={handleRetake}
                >
                  <IconSymbol name="arrow.counterclockwise" size={24} color="#FFFFFF" />
                  <ThemedText style={styles.previewButtonText}>Retake</ThemedText>
                </Pressable>

                <Pressable
                  style={({ pressed }) => [
                    styles.previewButton,
                    styles.printButton,
                    pressed && styles.buttonPressed,
                    isPrinting && styles.buttonDisabled,
                  ]}
                  onPress={handlePrint}
                  disabled={isPrinting}
                >
                  {isPrinting ? (
                    <ActivityIndicator color="#FFFFFF" />
                  ) : (
                    <>
                      <IconSymbol name="printer.fill" size={24} color="#FFFFFF" />
                      <ThemedText style={styles.previewButtonText}>Print</ThemedText>
                    </>
                  )}
                </Pressable>
              </View>
            </View>
          </View>
        </Modal>
      </ThemedView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#0F0F0F',
  },
  screen: {
    flex: 1,
    backgroundColor: '#0F0F0F',
  },
  header: {
    padding: 20,
    paddingBottom: 16,
  },
  title: {
    fontSize: 28,
    fontFamily: 'JetBrainsMono_700Bold',
    color: '#F9FAFB',
    marginBottom: 8,
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  statusText: {
    fontSize: 13,
    color: '#9CA3AF',
    fontFamily: 'JetBrainsMono_500Medium',
  },
  
  // Camera
  cameraContainer: {
    flex: 1,
    margin: 20,
    marginTop: 0,
    borderRadius: 16,
    overflow: 'hidden',
    backgroundColor: '#1A1A1A',
    borderWidth: 1,
    borderColor: 'rgba(37, 37, 37, 0.6)',
  },
  cameraImage: {
    width: '100%',
    height: '100%',
  },
  placeholderContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 16,
  },
  placeholderText: {
    fontSize: 14,
    color: '#9CA3AF',
    fontFamily: 'JetBrainsMono_500Medium',
  },
  listeningOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(59, 130, 246, 0.3)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  listeningIndicator: {
    backgroundColor: 'rgba(59, 130, 246, 0.9)',
    paddingHorizontal: 32,
    paddingVertical: 24,
    borderRadius: 20,
    alignItems: 'center',
    gap: 12,
  },
  listeningText: {
    fontSize: 16,
    fontFamily: 'JetBrainsMono_600SemiBold',
    color: '#FFFFFF',
  },
  
  // Controls
  controls: {
    flexDirection: 'row',
    paddingHorizontal: 20,
    paddingVertical: 16,
    gap: 12,
    alignItems: 'center',
  },
  voiceButton: {
    flex: 1,
    backgroundColor: 'rgba(59, 130, 246, 0.2)',
    borderWidth: 1,
    borderColor: 'rgba(59, 130, 246, 0.4)',
    borderRadius: 16,
    paddingVertical: 16,
    alignItems: 'center',
    gap: 6,
  },
  voiceButtonActive: {
    backgroundColor: 'rgba(239, 68, 68, 0.3)',
    borderColor: 'rgba(239, 68, 68, 0.6)',
  },
  captureButton: {
    flex: 2,
    backgroundColor: '#3B82F6',
    borderRadius: 16,
    paddingVertical: 18,
    alignItems: 'center',
    gap: 8,
    shadowColor: '#3B82F6',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  captureButtonText: {
    fontSize: 16,
    fontFamily: 'JetBrainsMono_600SemiBold',
    color: '#FFFFFF',
  },
  printerButton: {
    flex: 1,
    backgroundColor: 'rgba(26, 26, 26, 0.7)',
    borderWidth: 1,
    borderColor: 'rgba(37, 37, 37, 0.6)',
    borderRadius: 16,
    paddingVertical: 16,
    alignItems: 'center',
    gap: 6,
  },
  buttonText: {
    fontSize: 13,
    fontFamily: 'JetBrainsMono_500Medium',
    color: '#D1D5DB',
  },
  buttonPressed: {
    opacity: 0.7,
    transform: [{ scale: 0.97 }],
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  
  // Help
  helpSection: {
    paddingHorizontal: 20,
    paddingBottom: 20,
    alignItems: 'center',
  },
  helpTitle: {
    fontSize: 12,
    fontFamily: 'JetBrainsMono_600SemiBold',
    color: '#9CA3AF',
    marginBottom: 4,
  },
  helpText: {
    fontSize: 11,
    fontFamily: 'JetBrainsMono_400Regular',
    color: '#67686C',
  },
  
  // Preview Modal
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.95)',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
  },
  previewContainer: {
    width: '100%',
    maxWidth: 500,
    backgroundColor: '#1A1A1A',
    borderRadius: 20,
    padding: 20,
    borderWidth: 1,
    borderColor: 'rgba(37, 37, 37, 0.6)',
  },
  previewTitle: {
    fontSize: 20,
    fontFamily: 'JetBrainsMono_700Bold',
    color: '#F9FAFB',
    marginBottom: 16,
    textAlign: 'center',
  },
  previewImage: {
    width: '100%',
    height: 400,
    borderRadius: 12,
    marginBottom: 20,
  },
  previewActions: {
    flexDirection: 'row',
    gap: 12,
  },
  previewButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 16,
    borderRadius: 12,
  },
  retakeButton: {
    backgroundColor: 'rgba(107, 114, 128, 0.3)',
    borderWidth: 1,
    borderColor: 'rgba(107, 114, 128, 0.5)',
  },
  printButton: {
    backgroundColor: '#10B981',
    shadowColor: '#10B981',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  previewButtonText: {
    fontSize: 16,
    fontFamily: 'JetBrainsMono_600SemiBold',
    color: '#FFFFFF',
  },
});

