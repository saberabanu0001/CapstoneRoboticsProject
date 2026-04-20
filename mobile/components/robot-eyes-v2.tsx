import React, { useEffect, useState, useCallback } from 'react';
import { StyleSheet, View } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  withRepeat,
  withSequence,
  withSpring,
  Easing,
  interpolate,
  runOnJS,
} from 'react-native-reanimated';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import { DeviceMotion } from 'expo-sensors';

type Emotion = 
  | 'happy' 
  | 'excited' 
  | 'curious' 
  | 'thinking' 
  | 'neutral' 
  | 'love' 
  | 'sleepy' 
  | 'surprised' 
  | 'playful' 
  | 'bored'
  | 'angry'
  | 'sad'
  | 'confused'
  | 'scared'
  | 'squint'
  | 'aiming'
  | 'dizzy';

interface RobotEyesProps {
  emotion?: Emotion;
  isOnline?: boolean;
}

export function RobotEyes({ emotion = 'neutral', isOnline = true }: RobotEyesProps) {
  const [currentEmotion, setCurrentEmotion] = useState<Emotion>(emotion);
  const [isInteracting, setIsInteracting] = useState(false);
  const [lastInteractionTime, setLastInteractionTime] = useState(Date.now());
  const [tapCount, setTapCount] = useState(0);
  const [lastTapTime, setLastTapTime] = useState(0);
  
  // Animation values
  const blinkProgress = useSharedValue(0);
  const lookX = useSharedValue(0);
  const lookY = useSharedValue(0);
  const upperLidHeight = useSharedValue(0);
  const lowerLidHeight = useSharedValue(0);
  const pupilScale = useSharedValue(1);
  const glowIntensity = useSharedValue(0);
  const containerScale = useSharedValue(1);
  const wiggle = useSharedValue(0);
  const spinRotation = useSharedValue(0);

  // Motion detection with better shake threshold
  useEffect(() => {
    DeviceMotion.setUpdateInterval(50);
    let wasFlat = false;
    let wasUpsideDown = false;
    let shakeCount = 0;
    let lastShakeTime = 0;
    let shakeIntensities: number[] = [];
    
    const subscription = DeviceMotion.addListener((motionData) => {
      const { rotation, acceleration } = motionData;
      
      // Shake detection - require sustained high acceleration
      if (acceleration) {
        const magnitude = Math.sqrt(
          (acceleration.x || 0) ** 2 + 
          (acceleration.y || 0) ** 2 + 
          (acceleration.z || 0) ** 2
        );
        
        const now = Date.now();
        
        // Collect shake intensities over 200ms window
        if (magnitude > 3.0) { // Higher threshold - only strong movements
          shakeIntensities.push(magnitude);
          
          // Keep only recent shakes (last 200ms)
          shakeIntensities = shakeIntensities.filter(() => now - lastShakeTime < 200);
          
          if (shakeIntensities.length >= 3) { // Need at least 3 strong movements
            const avgIntensity = shakeIntensities.reduce((a, b) => a + b, 0) / shakeIntensities.length;
            
            if (avgIntensity > 3.5 && now - lastShakeTime > 800) { // Much higher threshold + cooldown
              lastShakeTime = now;
              shakeIntensities = [];
              handleShake();
            }
          }
        }
      }
      
      // Orientation detection
      if (rotation && !isInteracting) {
        const beta = Math.abs(rotation.beta || 0) * (180 / Math.PI);
        const gamma = (rotation.gamma || 0) * (180 / Math.PI);
        
        const isFlat = beta > 70;
        const isUpright = beta < 30 && Math.abs(gamma) < 30;
        const isUpsideDown = beta < 30 && Math.abs(gamma) > 150;
        
        // Lying flat
        if (isFlat && !wasFlat) {
          wasFlat = true;
          handlePhoneLaidDown();
        } else if (isUpright && wasFlat) {
          wasFlat = false;
          handlePhoneUpright();
        }
        
        // Upside down
        if (isUpsideDown && !wasUpsideDown) {
          wasUpsideDown = true;
          handleUpsideDown();
        } else if (!isUpsideDown && wasUpsideDown) {
          wasUpsideDown = false;
        }
      }
    });

    return () => subscription.remove();
  }, [isInteracting]);

  const handleShake = useCallback(() => {
    setLastInteractionTime(Date.now());
    setCurrentEmotion('dizzy');
    
    // Dizzy spinning animation
    spinRotation.value = withSequence(
      withTiming(360, { duration: 800, easing: Easing.out(Easing.ease) }),
      withTiming(720, { duration: 600, easing: Easing.linear }),
      withTiming(720, { duration: 0 })
    );
    
    wiggle.value = withSequence(
      withTiming(-8, { duration: 60 }),
      withRepeat(withSequence(withTiming(8, { duration: 60 }), withTiming(-8, { duration: 60 })), 5, true),
      withTiming(0, { duration: 60 })
    );
    
    setTimeout(() => {
      spinRotation.value = withTiming(0, { duration: 400 });
      setCurrentEmotion('confused');
      setTimeout(() => {
        setCurrentEmotion('happy');
        setTimeout(() => setCurrentEmotion(emotion), 1000);
      }, 1500);
    }, 2000);
  }, [emotion]);

  const handlePhoneLaidDown = useCallback(() => {
    setLastInteractionTime(Date.now());
    setCurrentEmotion('sleepy');
  }, []);

  const handlePhoneUpright = useCallback(() => {
    setLastInteractionTime(Date.now());
    if (currentEmotion === 'sleepy' || currentEmotion === 'bored') {
      setCurrentEmotion('surprised');
      setTimeout(() => setCurrentEmotion(emotion), 1500);
    }
  }, [emotion, currentEmotion]);

  const handleUpsideDown = useCallback(() => {
    setLastInteractionTime(Date.now());
    setCurrentEmotion('confused');
    setTimeout(() => setCurrentEmotion(emotion), 2500);
  }, [emotion]);

  const handleTouch = useCallback(() => {
    const now = Date.now();
    setLastInteractionTime(now);
    
    // Double tap detection
    if (now - lastTapTime < 400) {
      // Double tap!
      setIsInteracting(true);
      setCurrentEmotion('love');
      setTapCount(0);
      containerScale.value = withSequence(
        withSpring(1.15, { damping: 6 }),
        withSpring(0.95, { damping: 8 }),
        withSpring(1.1, { damping: 6 }),
        withSpring(1, { damping: 8 })
      );
      setTimeout(() => {
        setCurrentEmotion('happy');
        setTimeout(() => {
          setCurrentEmotion(emotion);
          setIsInteracting(false);
        }, 1000);
      }, 2000);
    } else {
      // Single tap
      setIsInteracting(true);
      setCurrentEmotion('excited');
      containerScale.value = withSequence(
        withSpring(1.1, { damping: 8 }),
        withSpring(1)
      );
      setTimeout(() => {
        setCurrentEmotion(emotion);
        setIsInteracting(false);
      }, 1200);
    }
    
    setLastTapTime(now);
    setTapCount(prev => prev + 1);
  }, [emotion, lastTapTime]);

  const handleLongPress = useCallback(() => {
    setLastInteractionTime(Date.now());
    setIsInteracting(true);
    setCurrentEmotion('love');
    
    // Gentle pulsing
    containerScale.value = withRepeat(
      withSequence(
        withTiming(1.05, { duration: 600, easing: Easing.inOut(Easing.ease) }),
        withTiming(1, { duration: 600, easing: Easing.inOut(Easing.ease) })
      ),
      2,
      false
    );
    
    setTimeout(() => {
      setCurrentEmotion('happy');
      setTimeout(() => {
        setCurrentEmotion(emotion);
        setIsInteracting(false);
      }, 800);
    }, 2400);
  }, [emotion]);

  // Update emotion when prop changes
  useEffect(() => {
    if (!isInteracting) {
      setCurrentEmotion(emotion);
    }
  }, [emotion, isInteracting]);

  // Boredom and idle state detection
  useEffect(() => {
    const checkIdle = setInterval(() => {
      const timeSinceInteraction = Date.now() - lastInteractionTime;
      
      if (!isInteracting && currentEmotion !== 'sleepy') {
        if (timeSinceInteraction > 45000) { // 45 seconds - very bored
          setCurrentEmotion('bored');
        } else if (timeSinceInteraction > 25000 && currentEmotion === emotion) { // 25 seconds - getting bored
          setCurrentEmotion('thinking');
          setTimeout(() => {
            if (Date.now() - lastInteractionTime > 30000) {
              setCurrentEmotion('bored');
            }
          }, 5000);
        }
      }
    }, 5000);
    
    return () => clearInterval(checkIdle);
  }, [lastInteractionTime, isInteracting, currentEmotion, emotion]);

  // Gestures
  const tapGesture = Gesture.Tap().onEnd(() => {
    'worklet';
    containerScale.value = withSequence(
      withSpring(1.1, { damping: 8 }),
      withSpring(1)
    );
    runOnJS(handleTouch)();
  });

  const longPressGesture = Gesture.LongPress().minDuration(500).onEnd(() => {
    'worklet';
    containerScale.value = withSequence(
      withSpring(1.08, { damping: 10 }),
      withSpring(1)
    );
    runOnJS(handleLongPress)();
  });

  const composedGestures = Gesture.Race(longPressGesture, tapGesture);

  // Get eye configuration based on emotion - simplified like RoboEyes library
  const getEyeConfig = () => {
    switch (currentEmotion) {
      case 'happy':
        return { upperLid: 0.35, lowerLid: 0, pupilScale: 1.0, lookSpeed: 2.0 };
      case 'excited':
        return { upperLid: 0.0, lowerLid: 0.0, pupilScale: 1.15, lookSpeed: 0.5 };
      case 'curious':
        return { upperLid: 0.0, lowerLid: 0.0, pupilScale: 1.05, lookSpeed: 1.5 };
      case 'thinking':
        return { upperLid: 0.2, lowerLid: 0.0, pupilScale: 0.95, lookSpeed: 2.5 };
      case 'love':
        return { upperLid: 0.3, lowerLid: 0.0, pupilScale: 1.0, lookSpeed: 2.5 };
      case 'sleepy':
        return { upperLid: 0.6, lowerLid: 0.1, pupilScale: 0.85, lookSpeed: 4.0 };
      case 'surprised':
        return { upperLid: 0.0, lowerLid: 0.0, pupilScale: 1.2, lookSpeed: 0.4 };
      case 'playful':
        return { upperLid: 0.0, lowerLid: 0.0, pupilScale: 1.1, lookSpeed: 0.6 };
      case 'bored':
        return { upperLid: 0.4, lowerLid: 0.0, pupilScale: 0.9, lookSpeed: 3.5 };
      case 'angry':
        return { upperLid: 0.25, lowerLid: 0.15, pupilScale: 1.0, lookSpeed: 1.2 };
      case 'sad':
        return { upperLid: 0.4, lowerLid: 0.0, pupilScale: 0.9, lookSpeed: 3.0 };
      case 'confused':
        return { upperLid: 0.1, lowerLid: 0.0, pupilScale: 1.05, lookSpeed: 1.5 };
      case 'scared':
        return { upperLid: 0.0, lowerLid: 0.0, pupilScale: 1.2, lookSpeed: 0.5 };
      case 'squint':
        return { upperLid: 0.5, lowerLid: 0.1, pupilScale: 0.85, lookSpeed: 2.5 };
      case 'aiming':
        return { upperLid: 0.15, lowerLid: 0.0, pupilScale: 1.0, lookSpeed: 1.0 };
      case 'dizzy':
        return { upperLid: 0.2, lowerLid: 0.0, pupilScale: 1.0, lookSpeed: 0.4 };
      default:
        return { upperLid: 0.0, lowerLid: 0.0, pupilScale: 1.0, lookSpeed: 2.0 };
    }
  };

  const eyeConfig = getEyeConfig();

  // Animate eyelids
  useEffect(() => {
    upperLidHeight.value = withTiming(eyeConfig.upperLid, { duration: 400, easing: Easing.out(Easing.ease) });
    lowerLidHeight.value = withTiming(eyeConfig.lowerLid, { duration: 400, easing: Easing.out(Easing.ease) });
    pupilScale.value = withTiming(eyeConfig.pupilScale, { duration: 400, easing: Easing.out(Easing.ease) });
  }, [currentEmotion]);

  // Blinking
  useEffect(() => {
    const startBlinking = () => {
      const randomDelay = 2000 + Math.random() * 3000;
      blinkProgress.value = withSequence(
        withTiming(0, { duration: 0 }),
        withTiming(1, { duration: 80, easing: Easing.out(Easing.ease) }),
        withTiming(1, { duration: 40 }),
        withTiming(0, { duration: 120, easing: Easing.in(Easing.ease) }),
        withTiming(0, { duration: randomDelay })
      );
    };

    blinkProgress.value = withRepeat(
      withSequence(
        withTiming(0, { duration: 3000 }),
        withTiming(1, { duration: 80 }),
        withTiming(0, { duration: 120 })
      ),
      -1,
      false
    );
  }, []);

  // Eye movement
  useEffect(() => {
    const duration = eyeConfig.lookSpeed * 1000;
    
    lookX.value = withRepeat(
      withSequence(
        withTiming(0.6, { duration: duration, easing: Easing.bezier(0.4, 0, 0.2, 1) }),
        withTiming(-0.5, { duration: duration * 1.5, easing: Easing.bezier(0.4, 0, 0.2, 1) }),
        withTiming(0, { duration: duration, easing: Easing.bezier(0.4, 0, 0.2, 1) })
      ),
      -1,
      false
    );

    lookY.value = withRepeat(
      withSequence(
        withTiming(0, { duration: duration * 1.5 }),
        withTiming(-0.3, { duration: duration, easing: Easing.bezier(0.4, 0, 0.2, 1) }),
        withTiming(0.2, { duration: duration * 1.2, easing: Easing.bezier(0.4, 0, 0.2, 1) }),
        withTiming(0, { duration: duration })
      ),
      -1,
      false
    );
  }, [currentEmotion]);

  // Glow animation
  useEffect(() => {
    if (isOnline) {
      glowIntensity.value = withRepeat(
        withSequence(
          withTiming(1, { duration: 2000, easing: Easing.inOut(Easing.ease) }),
          withTiming(0.5, { duration: 2000, easing: Easing.inOut(Easing.ease) })
        ),
        -1,
        false
      );
    } else {
      glowIntensity.value = 0.2;
    }
  }, [isOnline]);

  // Animated styles
  const containerStyle = useAnimatedStyle(() => ({
    transform: [
      { scale: containerScale.value },
      { rotate: `${wiggle.value + spinRotation.value}deg` }
    ],
  }));

  const eyeStyle = useAnimatedStyle(() => {
    const blinkScale = interpolate(blinkProgress.value, [0, 1], [1, 0.05]);
    const emotionScale = 1 - (upperLidHeight.value + lowerLidHeight.value * 0.5);
    
    return {
      transform: [
        { scaleY: blinkScale * Math.max(0.2, emotionScale) }
      ],
    };
  });

  const pupilAnimStyle = useAnimatedStyle(() => {
    const translateX = lookX.value * 8;
    const translateY = lookY.value * 6;
    
    return {
      transform: [
        { translateX },
        { translateY },
        { scale: pupilScale.value }
      ],
    };
  });

  const glowStyle = useAnimatedStyle(() => ({
    opacity: glowIntensity.value * 0.6,
  }));

  const eyeColor = isOnline ? '#34D399' : '#EF4444';
  const glowColor = isOnline ? 'rgba(52, 211, 153, 0.4)' : 'rgba(239, 68, 68, 0.4)';

  return (
    <GestureDetector gesture={composedGestures}>
      <Animated.View style={[styles.container, containerStyle]}>
        {/* Glow effect */}
        <Animated.View style={[styles.glowOuter, glowStyle]}>
          <View style={[styles.glowInner, { backgroundColor: glowColor }]} />
        </Animated.View>

        <View style={styles.eyesContainer}>
          {/* Left Eye */}
          <Animated.View style={[styles.eyeWhite, eyeStyle]}>
            <Animated.View style={pupilAnimStyle}>
              <View style={[styles.pupil, { backgroundColor: eyeColor }]}>
                <View style={styles.highlight} />
              </View>
            </Animated.View>
          </Animated.View>

          {/* Right Eye */}
          <Animated.View style={[styles.eyeWhite, eyeStyle]}>
            <Animated.View style={pupilAnimStyle}>
              <View style={[styles.pupil, { backgroundColor: eyeColor }]}>
                <View style={styles.highlight} />
              </View>
            </Animated.View>
          </Animated.View>
        </View>
      </Animated.View>
    </GestureDetector>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 40,
    paddingHorizontal: 24,
    minHeight: 160,
  },
  glowOuter: {
    position: 'absolute',
    width: '100%',
    height: '100%',
    alignItems: 'center',
    justifyContent: 'center',
  },
  glowInner: {
    width: 240,
    height: 100,
    borderRadius: 50,
  },
  eyesContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 40,
  },
  eyeWhite: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: '#F9FAFB',
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 6,
  },
  pupil: {
    width: 38,
    height: 38,
    borderRadius: 19,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.4,
    shadowRadius: 4,
    elevation: 4,
  },
  highlight: {
    position: 'absolute',
    top: 8,
    left: 10,
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
  },
});

