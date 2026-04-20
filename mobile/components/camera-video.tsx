import { Image } from 'expo-image';
import React, { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Dimensions, Pressable, StyleSheet, View } from 'react-native';
import Animated, { 
  useSharedValue, 
  useAnimatedStyle, 
  withTiming, 
  withRepeat,
  withSequence,
  Easing,
  runOnJS,
  interpolate,
} from 'react-native-reanimated';

import { ThemedText } from '@/components/themed-text';

interface CameraVideoProps {
     wsUrl?: string;
     currentFrame: string | null;
     isConnecting: boolean;
     isStreaming: boolean;
     error: string | null;
     onToggleStream: () => void;
     detectedGesture?: 'like' | 'heart' | 'none';
}

export function CameraVideo({
     wsUrl,
     currentFrame,
     isConnecting,
     isStreaming,
     error,
     onToggleStream,
     detectedGesture = 'none',
}: CameraVideoProps) {
     const [hearts, setHearts] = useState<Array<{ id: number; startX: number }>>([]);
     const heartIdRef = useRef(0);

     // Create hearts when heart gesture is detected
     useEffect(() => {
          if (detectedGesture === 'heart') {
               // Create 3 hearts at random X positions
               const newHearts = Array.from({ length: 3 }, () => {
                    heartIdRef.current += 1;
                    return {
                         id: heartIdRef.current,
                         startX: Math.random() * Dimensions.get('window').width,
                    };
               });
               setHearts((prev) => [...prev, ...newHearts]);
          }
     }, [detectedGesture]);

     return (
          <View style={styles.cameraFrame}>
               <View style={styles.streamArea}>
                    {wsUrl ? (
                         <>
                              {currentFrame ? (
                                   <>
                                        <Image
                                             source={{ uri: currentFrame }}
                                             style={[styles.camera, styles.mirrored]}
                                             contentFit="contain"
                                             cachePolicy="none"
                                             transition={null}
                                        />
                                        {/* Animated hearts overlay */}
                                        {hearts.map((heart) => (
                                             <AnimatedHeart
                                                  key={heart.id}
                                                  startX={heart.startX}
                                                  onComplete={() => {
                                                       setHearts((prev) => prev.filter((h) => h.id !== heart.id));
                                                  }}
                                             />
                                        ))}
                                   </>
                              ) : (
                                   <View style={styles.placeholderContainer}>
                                        {isConnecting ? (
                                             <>
                                                  <ActivityIndicator size="large" color="#1DD1A1" />
                                                  <ThemedText style={styles.placeholderText}>
                                                       Connecting to camera...
                                                  </ThemedText>
                                             </>
                                        ) : (
                                             <ThemedText style={styles.placeholderText}>
                                                  {isStreaming
                                                       ? 'Waiting for video...'
                                                       : 'Press Start to begin streaming'}
                                             </ThemedText>
                                        )}
                                   </View>
                              )}

                              {error && (
                                   <View style={styles.errorOverlay}>
                                        <ThemedText style={styles.errorText}>{error}</ThemedText>
                                        <ThemedText style={styles.errorSubtext}>
                                             WebSocket: {wsUrl}
                                        </ThemedText>
                                        <Pressable style={styles.retryButton} onPress={onToggleStream}>
                                             <ThemedText style={styles.retryButtonText}>Retry Connection</ThemedText>
                                        </Pressable>
                                   </View>
                              )}
                         </>
                    ) : (
                         <View style={styles.loadingContainer}>
                              <ActivityIndicator size="large" color="#1DD1A1" />
                              <ThemedText style={styles.loadingText}>
                                   No stream available. Configure the robot IP first.
                              </ThemedText>
                         </View>
                    )}
               </View>
          </View>
     );
}

const styles = StyleSheet.create({
     cameraFrame: {
          flexDirection: 'column',
          borderRadius: 0,
          overflow: 'hidden',
          borderWidth: 1,
          borderColor: '#202020',
          aspectRatio: 4 / 3,
          backgroundColor: '#1B1B1B',
          alignItems: 'center',
          justifyContent: 'space-between',
          zIndex: 0
     },
     streamArea: {
          flex: 1,
          width: Dimensions.get("window").width,
          alignItems: 'center',
          justifyContent: 'center',
     },
     camera: {
          width: '100%',
          height: '100%',
     },
     mirrored: {
          transform: [{ scaleX: -1 }], // Mirror/flip horizontally
     },
     placeholderContainer: {
          flex: 1,
          alignItems: 'center',
          justifyContent: 'center',
          gap: 16,
     },
     placeholderText: {
          color: '#6B7280',
          fontSize: 14,
          textAlign: 'center',
     },
     loadingContainer: {
          flex: 1,
          alignItems: 'center',
          justifyContent: 'center',
          gap: 16,
     },
     loadingText: {
          color: '#67686C',
          textAlign: 'center',
          paddingHorizontal: 24,
     },
     errorOverlay: {
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 24,
          gap: 12,
     },
     errorText: {
          color: '#EF4444',
          fontSize: 16,
          textAlign: 'center',
     },
     errorSubtext: {
          color: '#67686C',
          fontSize: 10,
          textAlign: 'center',
          fontFamily: 'JetBrainsMono_400Regular',
     },
     retryButton: {
          marginTop: 8,
          paddingVertical: 8,
          paddingHorizontal: 16,
          backgroundColor: '#1DD1A1',
          borderRadius: 4,
     },
     retryButtonText: {
          color: '#04110B',
          fontSize: 14,
          fontWeight: '600',
     },
     lightControls: {
          width: '100%',
          padding: 12,
          borderTopWidth: 1,
          borderTopColor: '#202020',
          backgroundColor: '#0F1512',
          gap: 8,
     },
     lightLabel: {
          color: '#E5E7EB',
          fontSize: 14,
          fontWeight: '600',
     },
     lightButtons: {
          flexDirection: 'row',
          gap: 12,
          width: '100%',
     },
     pairingNotice: {
          flexDirection: 'row',
          alignItems: 'center',
          gap: 8,
     },
     pairingText: {
          color: '#9CA3AF',
          flex: 1,
          fontSize: 12,
     },
     pairingButton: {
          borderWidth: 1,
          borderColor: '#1DD1A1',
          paddingVertical: 8,
          paddingHorizontal: 12,
          borderRadius: 6,
     },
     pairingButtonText: {
          color: '#1DD1A1',
          fontWeight: '600',
          fontSize: 12,
     },
     lightButton: {
          flex: 1,
          paddingVertical: 10,
          borderRadius: 6,
          alignItems: 'center',
          justifyContent: 'center',
          borderWidth: 1,
          borderColor: '#1DD1A1',
     },
     lightButtonSecondary: {
          backgroundColor: '#0B1612',
     },
     lightButtonPrimary: {
          backgroundColor: '#1DD1A1',
          borderColor: '#1DD1A1',
     },
     lightButtonDisabled: {
          opacity: 0.6,
     },
     lightButtonText: {
          color: '#E5E7EB',
          fontWeight: '600',
     },
     lightButtonTextDark: {
          color: '#04110B',
          fontWeight: '700',
     },
     heartContainer: {
          position: 'absolute',
          zIndex: 1000,
     },
     heartText: {
          fontSize: 32,
     },
});

// Animated heart component that floats up and fades out
function AnimatedHeart({ startX, onComplete }: { startX: number; onComplete: () => void }) {
     const translateY = useSharedValue(0);
     const opacity = useSharedValue(1);
     const scale = useSharedValue(0.5);

     useEffect(() => {
          // Animate heart floating up, scaling, and fading out
          translateY.value = withTiming(-Dimensions.get('window').height, {
               duration: 3000,
               easing: Easing.out(Easing.cubic),
          });
          opacity.value = withSequence(
               withTiming(1, { duration: 500 }),
               withTiming(0, { duration: 2500 })
          );
          scale.value = withSequence(
               withTiming(1, { duration: 300, easing: Easing.out(Easing.back(2)) }),
               withTiming(1.2, { duration: 2700, easing: Easing.in(Easing.ease) })
          );

          // Call onComplete after animation
          const timer = setTimeout(() => {
               runOnJS(onComplete)();
          }, 3000);

          return () => clearTimeout(timer);
     }, []);

     const animatedStyle = useAnimatedStyle(() => ({
          transform: [
               { translateY: translateY.value },
               { translateX: -16 }, // Center the heart icon (half of font size)
               { scale: scale.value },
          ],
          opacity: opacity.value,
     }));

     return (
          <Animated.View
               style={[
                    styles.heartContainer,
                    {
                         left: startX,
                         top: Dimensions.get('window').height - 100,
                    },
                    animatedStyle,
               ]}
               pointerEvents="none"
          >
               <ThemedText style={styles.heartText}>❤️</ThemedText>
          </Animated.View>
     );
}
