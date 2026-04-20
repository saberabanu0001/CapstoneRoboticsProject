import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
     ActivityIndicator,
     Dimensions,
     Image,
     Platform,
     Pressable,
     StatusBar,
     StyleSheet,
     Text,
     View,
} from 'react-native';
import { Gesture, GestureDetector, GestureHandlerRootView } from 'react-native-gesture-handler';
import Animated, {
     runOnJS,
     useAnimatedStyle,
     useSharedValue,
     withSpring,
} from 'react-native-reanimated';
import * as ScreenOrientation from 'expo-screen-orientation';
import { useRouter } from 'expo-router';

import { IconSymbol } from '@/components/ui/icon-symbol';
import { useRobot } from '@/context/robot-provider';
import {
     cmdJsonCmd,
     cmd_movition_ctrl,
     cmd_lights_ctrl,
     cmd_gimbal_ctrl,
     max_speed,
     GimbalCommand,
} from '@/services/json-socket';

const JOYSTICK_SIZE = 140;
const JOYSTICK_KNOB_SIZE = 60;
const JOYSTICK_MAX_DISTANCE = (JOYSTICK_SIZE - JOYSTICK_KNOB_SIZE) / 2;

export default function ManualScreen() {
     const { baseUrl } = useRobot();
     const router = useRouter();

     // Stream state
     const [currentFrame, setCurrentFrame] = useState<string | null>(null);
     const [isStreaming, setIsStreaming] = useState(false);
     const [isConnecting, setIsConnecting] = useState(false);
     const [error, setError] = useState<string | null>(null);
     const [isLightOn, setIsLightOn] = useState(false);
     const wsRef = useRef<WebSocket | null>(null);

     // Gimbal state
     const [gimbalPos, setGimbalPos] = useState({ x: 0, y: 0 });
     const gimbalRef = useRef({ x: 0, y: 0 });

     // Joystick animated values
     const joystickX = useSharedValue(0);
     const joystickY = useSharedValue(0);
     const joystickActive = useSharedValue(false);

     // Force landscape orientation on mount
     useEffect(() => {
          const lockToLandscape = async () => {
               try {
                    // First unlock any existing lock
                    await ScreenOrientation.unlockAsync();
                    // Then lock to landscape
                    await ScreenOrientation.lockAsync(
                         ScreenOrientation.OrientationLock.LANDSCAPE
                    );
                    console.log('Orientation locked to landscape');
               } catch (err) {
                    console.warn('Failed to lock orientation:', err);
               }
          };
          
          lockToLandscape();

          return () => {
               // Force back to portrait when leaving this screen
               const resetToPortrait = async () => {
                    try {
                         await ScreenOrientation.lockAsync(
                              ScreenOrientation.OrientationLock.PORTRAIT_UP
                         );
                         console.log('Orientation reset to portrait');
                    } catch (err) {
                         console.warn('Failed to reset orientation:', err);
                    }
               };
               resetToPortrait();
          };
     }, []);

     // WebSocket URL
     const wsUrl = useMemo(() => {
          if (!baseUrl) return undefined;
          try {
               const normalizedUrl = baseUrl.startsWith('http')
                    ? baseUrl
                    : `http://${baseUrl}`;
               const parsedUrl = new URL(normalizedUrl);
               const host = parsedUrl.hostname;
               const isIp = /^\d{1,3}(\.\d{1,3}){3}$/.test(host) || host === 'localhost';
               parsedUrl.protocol = isIp ? 'ws:' : parsedUrl.protocol === 'https:' ? 'wss:' : 'ws:';
               parsedUrl.pathname = `${parsedUrl.pathname.replace(/\/$/, '')}/camera/ws`;
               parsedUrl.search = '';
               return parsedUrl.toString();
          } catch {
               return undefined;
          }
     }, [baseUrl]);

     // WebSocket connection
     const connectWebSocket = useCallback(() => {
          if (!wsUrl) {
               setError('No WebSocket URL available');
               return;
          }

          if (wsRef.current) {
               wsRef.current.close();
               wsRef.current = null;
          }

          setIsConnecting(true);
          setError(null);

          const connectionTimeout = setTimeout(() => {
               if (wsRef.current?.readyState === WebSocket.CONNECTING) {
                    wsRef.current.close();
                    setError('Connection timeout');
                    setIsConnecting(false);
               }
          }, 10000);

          const ws = new WebSocket(wsUrl);
          wsRef.current = ws;

          ws.onopen = () => {
               clearTimeout(connectionTimeout);
               setIsConnecting(false);
               setIsStreaming(true);
               setError(null);
          };

          ws.onmessage = (event) => {
               try {
                    const data = JSON.parse(event.data);
                    if (data.error) {
                         setError(data.error);
                         return;
                    }
                    if (data.frame) {
                         setCurrentFrame(`data:image/jpeg;base64,${data.frame}`);
                    }
               } catch {
                    // Ignore parse errors
               }
          };

          ws.onerror = () => {
               clearTimeout(connectionTimeout);
               setError('Connection failed');
               setIsConnecting(false);
               setIsStreaming(false);
          };

          ws.onclose = (event) => {
               clearTimeout(connectionTimeout);
               setIsStreaming(false);
               setIsConnecting(false);
               if (!event.wasClean && event.code === 1006) {
                    setError('Connection lost');
               }
          };
     }, [wsUrl]);

     const disconnectWebSocket = useCallback(() => {
          if (wsRef.current) {
               wsRef.current.close();
               wsRef.current = null;
          }
          setIsStreaming(false);
          setIsConnecting(false);
          setCurrentFrame(null);
     }, []);

     // Auto-connect
     useEffect(() => {
          if (wsUrl && !isStreaming && !isConnecting) {
               connectWebSocket();
          }
     }, [wsUrl, isStreaming, isConnecting, connectWebSocket]);

     // Cleanup
     useEffect(() => {
          return () => {
               disconnectWebSocket();
          };
     }, [disconnectWebSocket]);

     // Send movement command
     const sendMovement = useCallback(
          (left: number, right: number) => {
               cmdJsonCmd({ T: cmd_movition_ctrl, L: left, R: right }, baseUrl);
          },
          [baseUrl]
     );

     // Send gimbal command
     const sendGimbal = useCallback(
          (x: number, y: number) => {
               const command: GimbalCommand = {
                    T: cmd_gimbal_ctrl,
                    X: Math.round(x),
                    Y: Math.round(y),
                    SPD: 20,
               };
               cmdJsonCmd(command, baseUrl);
          },
          [baseUrl]
     );

     // Joystick gesture
     const joystickGesture = Gesture.Pan()
          .onBegin(() => {
               joystickActive.value = true;
          })
          .onUpdate((event) => {
               const distance = Math.sqrt(event.translationX ** 2 + event.translationY ** 2);
               const clampedDistance = Math.min(distance, JOYSTICK_MAX_DISTANCE);
               const angle = Math.atan2(event.translationY, event.translationX);

               joystickX.value = Math.cos(angle) * clampedDistance;
               joystickY.value = Math.sin(angle) * clampedDistance;

               // Calculate motor speeds (tank drive)
               const normalizedX = joystickX.value / JOYSTICK_MAX_DISTANCE;
               const normalizedY = -joystickY.value / JOYSTICK_MAX_DISTANCE; // Invert Y

               // Tank drive calculation (negated for reversed motors)
               const leftSpeed = -(normalizedY + normalizedX) * max_speed;
               const rightSpeed = -(normalizedY - normalizedX) * max_speed;

               runOnJS(sendMovement)(leftSpeed, rightSpeed);
          })
          .onEnd(() => {
               joystickX.value = withSpring(0, { damping: 15, stiffness: 150 });
               joystickY.value = withSpring(0, { damping: 15, stiffness: 150 });
               joystickActive.value = false;
               runOnJS(sendMovement)(0, 0);
          });

     const joystickKnobStyle = useAnimatedStyle(() => ({
          transform: [
               { translateX: joystickX.value },
               { translateY: joystickY.value },
          ],
     }));

     // Gimbal gesture (touch on video area)
     const gimbalGesture = Gesture.Pan()
          .onUpdate((event) => {
               // Map screen position to gimbal angles
               // Pan: -180 to 180, Tilt: -30 to 90
               const panDelta = event.translationX * 0.5;
               const tiltDelta = -event.translationY * 0.3;

               const newX = Math.max(-180, Math.min(180, gimbalRef.current.x + panDelta));
               const newY = Math.max(-30, Math.min(90, gimbalRef.current.y + tiltDelta));

               runOnJS(sendGimbal)(newX, newY);
          })
          .onEnd((event) => {
               // Update stored position
               const panDelta = event.translationX * 0.5;
               const tiltDelta = -event.translationY * 0.3;

               gimbalRef.current.x = Math.max(-180, Math.min(180, gimbalRef.current.x + panDelta));
               gimbalRef.current.y = Math.max(-30, Math.min(90, gimbalRef.current.y + tiltDelta));

               runOnJS(setGimbalPos)({ ...gimbalRef.current });
          });

     // Light control
     const handleLightToggle = useCallback(() => {
          cmdJsonCmd(
               { T: cmd_lights_ctrl, IO4: isLightOn ? 0 : 115, IO5: isLightOn ? 0 : 115 },
               baseUrl
          );
          setIsLightOn(!isLightOn);
     }, [baseUrl, isLightOn]);

     // Center gimbal
     const handleCenterGimbal = useCallback(() => {
          gimbalRef.current = { x: 0, y: 0 };
          setGimbalPos({ x: 0, y: 0 });
          sendGimbal(0, 0);
     }, [sendGimbal]);

     return (
          <GestureHandlerRootView style={styles.container}>
               <StatusBar hidden />

               {/* Fullscreen Camera Feed */}
               <GestureDetector gesture={gimbalGesture}>
                    <Animated.View style={styles.cameraContainer}>
                         {currentFrame ? (
                              <Image source={{ uri: currentFrame }} style={styles.cameraFeed} resizeMode="cover" />
                         ) : (
                              <View style={styles.cameraPlaceholder}>
                                   {isConnecting ? (
                                        <ActivityIndicator size="large" color="#1DD1A1" />
                                   ) : error ? (
                                        <Text style={styles.errorText}>{error}</Text>
                                   ) : (
                                        <Text style={styles.placeholderText}>Connecting camera...</Text>
                                   )}
                              </View>
                         )}

                         {/* Gimbal crosshair overlay */}
                         <View style={styles.crosshairContainer} pointerEvents="none">
                              <View style={styles.crosshairH} />
                              <View style={styles.crosshairV} />
                              <View style={styles.crosshairCenter} />
                         </View>

                         {/* Touch hint */}
                         <View style={styles.touchHint} pointerEvents="none">
                              <Text style={styles.touchHintText}>Drag to aim</Text>
                         </View>
                    </Animated.View>
               </GestureDetector>

               {/* HUD Overlay */}
               <View style={styles.hudContainer} pointerEvents="box-none">
                    {/* Top bar */}
                    <View style={styles.topBar}>
                         {/* Back button */}
                         <Pressable style={styles.hudButton} onPress={() => router.back()}>
                              <IconSymbol name="xmark" size={20} color="#FFF" />
                         </Pressable>

                         {/* Status */}
                         <View style={styles.statusPill}>
                              <View
                                   style={[
                                        styles.statusDot,
                                        { backgroundColor: isStreaming ? '#34D399' : isConnecting ? '#FBBF24' : '#EF4444' },
                                   ]}
                              />
                              <Text style={styles.statusText}>
                                   {isStreaming ? 'LIVE' : isConnecting ? 'CONNECTING' : 'OFFLINE'}
                              </Text>
                         </View>

                         {/* Gimbal position */}
                         <View style={styles.gimbalInfo}>
                              <Text style={styles.gimbalText}>
                                   PAN: {gimbalPos.x.toFixed(0)}° | TILT: {gimbalPos.y.toFixed(0)}°
                              </Text>
                         </View>
                    </View>

                    {/* Right side controls */}
                    <View style={styles.rightControls}>
                         {/* Light toggle */}
                         <Pressable
                              style={[styles.hudButton, isLightOn && styles.hudButtonActive]}
                              onPress={handleLightToggle}
                         >
                              <IconSymbol name="bolt.fill" size={22} color={isLightOn ? '#1DD1A1' : '#FFF'} />
                         </Pressable>

                         {/* Center gimbal */}
                         <Pressable style={styles.hudButton} onPress={handleCenterGimbal}>
                              <IconSymbol name="scope" size={22} color="#FFF" />
                         </Pressable>

                         {/* Reconnect */}
                         <Pressable style={styles.hudButton} onPress={connectWebSocket}>
                              <IconSymbol name="arrow.clockwise" size={22} color="#FFF" />
                         </Pressable>
                    </View>

                    {/* Joystick (bottom left) */}
                    <View style={styles.joystickContainer}>
                         <GestureDetector gesture={joystickGesture}>
                              <Animated.View style={styles.joystickBase}>
                                   <Animated.View style={[styles.joystickKnob, joystickKnobStyle]}>
                                        <View style={styles.joystickKnobInner} />
                                   </Animated.View>
                              </Animated.View>
                         </GestureDetector>
                    </View>

                    {/* Emergency stop (bottom right) */}
                    <View style={styles.emergencyContainer}>
                         <Pressable
                              style={styles.emergencyButton}
                              onPress={() => sendMovement(0, 0)}
                         >
                              <Text style={styles.emergencyText}>STOP</Text>
                         </Pressable>
                    </View>
               </View>
          </GestureHandlerRootView>
     );
}

const styles = StyleSheet.create({
     container: {
          flex: 1,
          backgroundColor: '#000',
     },
     cameraContainer: {
          flex: 1,
          backgroundColor: '#0A0A0A',
     },
     cameraFeed: {
          flex: 1,
          width: '100%',
          height: '100%',
     },
     cameraPlaceholder: {
          flex: 1,
          alignItems: 'center',
          justifyContent: 'center',
     },
     placeholderText: {
          color: '#666',
          fontSize: 16,
     },
     errorText: {
          color: '#EF4444',
          fontSize: 16,
     },

     // Crosshair
     crosshairContainer: {
          position: 'absolute',
          top: '50%',
          left: '50%',
          width: 60,
          height: 60,
          marginLeft: -30,
          marginTop: -30,
          alignItems: 'center',
          justifyContent: 'center',
     },
     crosshairH: {
          position: 'absolute',
          width: 40,
          height: 1,
          backgroundColor: 'rgba(29, 209, 161, 0.6)',
     },
     crosshairV: {
          position: 'absolute',
          width: 1,
          height: 40,
          backgroundColor: 'rgba(29, 209, 161, 0.6)',
     },
     crosshairCenter: {
          width: 8,
          height: 8,
          borderRadius: 4,
          borderWidth: 1,
          borderColor: 'rgba(29, 209, 161, 0.8)',
     },

     // Touch hint
     touchHint: {
          position: 'absolute',
          bottom: 100,
          left: '50%',
          transform: [{ translateX: -50 }],
     },
     touchHintText: {
          color: 'rgba(255, 255, 255, 0.4)',
          fontSize: 12,
          fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
     },

     // HUD
     hudContainer: {
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
     },

     // Top bar
     topBar: {
          flexDirection: 'row',
          alignItems: 'center',
          paddingHorizontal: 16,
          paddingTop: Platform.OS === 'ios' ? 16 : 8,
          gap: 12,
     },
     hudButton: {
          width: 44,
          height: 44,
          borderRadius: 22,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          alignItems: 'center',
          justifyContent: 'center',
          borderWidth: 1,
          borderColor: 'rgba(255, 255, 255, 0.1)',
     },
     hudButtonActive: {
          backgroundColor: 'rgba(29, 209, 161, 0.2)',
          borderColor: '#1DD1A1',
     },
     statusPill: {
          flexDirection: 'row',
          alignItems: 'center',
          paddingHorizontal: 12,
          paddingVertical: 6,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          borderRadius: 20,
          gap: 6,
     },
     statusDot: {
          width: 8,
          height: 8,
          borderRadius: 4,
     },
     statusText: {
          color: '#FFF',
          fontSize: 12,
          fontWeight: '600',
          fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
     },
     gimbalInfo: {
          marginLeft: 'auto',
          paddingHorizontal: 12,
          paddingVertical: 6,
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          borderRadius: 8,
     },
     gimbalText: {
          color: 'rgba(255, 255, 255, 0.7)',
          fontSize: 11,
          fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
     },

     // Right controls
     rightControls: {
          position: 'absolute',
          right: 16,
          top: '50%',
          transform: [{ translateY: -80 }],
          gap: 12,
     },

     // Joystick
     joystickContainer: {
          position: 'absolute',
          left: 40,
          bottom: 40,
     },
     joystickBase: {
          width: JOYSTICK_SIZE,
          height: JOYSTICK_SIZE,
          borderRadius: JOYSTICK_SIZE / 2,
          backgroundColor: 'rgba(30, 30, 32, 0.8)',
          borderWidth: 2,
          borderColor: 'rgba(42, 43, 48, 0.8)',
          alignItems: 'center',
          justifyContent: 'center',
     },
     joystickKnob: {
          width: JOYSTICK_KNOB_SIZE,
          height: JOYSTICK_KNOB_SIZE,
          borderRadius: JOYSTICK_KNOB_SIZE / 2,
          backgroundColor: 'rgba(42, 43, 48, 0.9)',
          alignItems: 'center',
          justifyContent: 'center',
          shadowColor: '#000',
          shadowOffset: { width: 0, height: 4 },
          shadowOpacity: 0.3,
          shadowRadius: 8,
          elevation: 8,
     },
     joystickKnobInner: {
          width: JOYSTICK_KNOB_SIZE - 16,
          height: JOYSTICK_KNOB_SIZE - 16,
          borderRadius: (JOYSTICK_KNOB_SIZE - 16) / 2,
          backgroundColor: '#1DD1A1',
          opacity: 0.8,
     },

     // Emergency stop
     emergencyContainer: {
          position: 'absolute',
          right: 40,
          bottom: 40,
     },
     emergencyButton: {
          width: 80,
          height: 80,
          borderRadius: 40,
          backgroundColor: 'rgba(239, 68, 68, 0.9)',
          alignItems: 'center',
          justifyContent: 'center',
          borderWidth: 3,
          borderColor: '#FCA5A5',
          shadowColor: '#EF4444',
          shadowOffset: { width: 0, height: 0 },
          shadowOpacity: 0.5,
          shadowRadius: 12,
          elevation: 10,
     },
     emergencyText: {
          color: '#FFF',
          fontSize: 14,
          fontWeight: '800',
          letterSpacing: 1,
     },
});
