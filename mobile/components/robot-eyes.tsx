import React, { useEffect, useState, useCallback } from 'react';
import { StyleSheet, View } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withTiming,
  withRepeat,
  withSequence,
  withDelay,
  withSpring,
  Easing,
  interpolate,
  runOnJS,
} from 'react-native-reanimated';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import { DeviceMotion } from 'expo-sensors';

type Emotion = 'happy' | 'excited' | 'curious' | 'thinking' | 'neutral' | 'love' | 'sleepy' | 'surprised' | 'playful' | 'bored' | 'confused';

interface RobotEyesProps {
  emotion?: Emotion;
  isOnline?: boolean;
}

type EyeStyle = 'normal';
type LidCurve = 'normal' | 'smile' | 'raised' | 'droopy' | 'asymmetric';

export function RobotEyes({ emotion = 'neutral', isOnline = true }: RobotEyesProps) {
  const [currentEmotion, setCurrentEmotion] = useState<Emotion>(emotion);
  const [isInteracting, setIsInteracting] = useState(false);
  const [lastInteractionTime, setLastInteractionTime] = useState(Date.now());
  
  const blinkProgress = useSharedValue(0);
  const lookProgress = useSharedValue(0);
  const glowProgress = useSharedValue(0);
  const scaleValue = useSharedValue(1);
  const bounceValue = useSharedValue(0);
  const lastShakeTime = useSharedValue(0);
  const wiggleValue = useSharedValue(0);
  const heartBeatScale = useSharedValue(1);
  
  // Boredom detection - if no interaction for a while
  useEffect(() => {
    const checkBoredom = setInterval(() => {
      const timeSinceInteraction = Date.now() - lastInteractionTime;
      
      if (!isInteracting && currentEmotion !== 'bored' && currentEmotion !== 'sleepy') {
        if (timeSinceInteraction > 30000) { // 30 seconds
          setCurrentEmotion('bored');
        }
      }
    }, 5000);
    
    return () => clearInterval(checkBoredom);
  }, [lastInteractionTime, isInteracting, currentEmotion]);
  
  // Motion detection
  useEffect(() => {
    DeviceMotion.setUpdateInterval(100);
    let wasFlat = false;
    
    const subscription = DeviceMotion.addListener((motionData) => {
      const { rotation, acceleration } = motionData;
      
      // Detect shake using acceleration (Playing with robot!)
      if (acceleration) {
        const magnitude = Math.sqrt(
          (acceleration.x || 0) ** 2 + 
          (acceleration.y || 0) ** 2 + 
          (acceleration.z || 0) ** 2
        );
        
        if (magnitude > 2.5 && Date.now() - lastShakeTime.value > 2000) {
          lastShakeTime.value = Date.now();
          handleShake();
        }
      }
      
      // Detect phone orientation
      if (rotation && !isInteracting) {
        const beta = Math.abs(rotation.beta || 0) * (180 / Math.PI);
        const isFlat = beta > 70; // Phone is lying flat
        
        if (isFlat && !wasFlat) {
          // Just laid down
          wasFlat = true;
          handlePhoneLaidDown();
        } else if (!isFlat && wasFlat) {
          // Just picked up
          wasFlat = false;
          handlePhoneUpright();
        }
      }
    });

    return () => subscription.remove();
  }, [isInteracting]);

  const handleShake = useCallback(() => {
    setLastInteractionTime(Date.now());
    // Shaking = Playing/Dancing with robot (excited and playful!)
    setCurrentEmotion('playful');
    
    // Wiggle/dance animation
    wiggleValue.value = withSequence(
      withTiming(-8, { duration: 80 }),
      withRepeat(
        withSequence(
          withTiming(8, { duration: 80 }),
          withTiming(-8, { duration: 80 })
        ),
        4,
        true
      ),
      withTiming(0, { duration: 80 })
    );
    
    bounceValue.value = withSequence(
      withSpring(-15, { damping: 6 }),
      withSpring(0)
    );
    
    setTimeout(() => {
      setCurrentEmotion('happy');
      setTimeout(() => setCurrentEmotion(emotion), 1500);
    }, 2000);
  }, [emotion]);

  const handlePhoneLaidDown = useCallback(() => {
    setLastInteractionTime(Date.now());
    // Phone laid down = Robot is resting/sleeping
    setCurrentEmotion('sleepy');
    setTimeout(() => setCurrentEmotion(emotion), 5000);
  }, [emotion]);
  
  const handlePhoneUpright = useCallback(() => {
    setLastInteractionTime(Date.now());
    // Phone picked up = Robot wakes up excited!
    if (currentEmotion === 'sleepy' || currentEmotion === 'bored') {
      setCurrentEmotion('surprised');
      scaleValue.value = withSequence(
        withSpring(1.15, { damping: 8 }),
        withSpring(1)
      );
      setTimeout(() => setCurrentEmotion(emotion), 1500);
    }
  }, [emotion, currentEmotion]);

  const handleTouch = useCallback(() => {
    setLastInteractionTime(Date.now());
    setIsInteracting(true);
    
    // Quick tap = Getting robot's attention (excited!)
    scaleValue.value = withSequence(
      withSpring(1.1, { damping: 8 }),
      withSpring(1)
    );
    setCurrentEmotion('excited');
    setTimeout(() => {
      setCurrentEmotion(emotion);
      setIsInteracting(false);
    }, 1500);
  }, [emotion]);

  const handleLongPress = useCallback(() => {
    setLastInteractionTime(Date.now());
    setIsInteracting(true);
    
    // Long press = Petting the robot (shows love!)
    setCurrentEmotion('love');
    
    // Heartbeat animation
    heartBeatScale.value = 1;
    heartBeatScale.value = withRepeat(
      withSequence(
        withTiming(1.15, { duration: 400 }),
        withTiming(1, { duration: 400 })
      ),
      3,
      false
    );
    
    scaleValue.value = withSequence(
      withSpring(1.08, { damping: 10 }),
      withSpring(1)
    );
    
    setTimeout(() => {
      setCurrentEmotion('happy');
      setTimeout(() => {
        setCurrentEmotion(emotion);
        setIsInteracting(false);
      }, 1000);
    }, 2500);
  }, [emotion]);

  // Update current emotion when prop changes
  useEffect(() => {
    if (!isInteracting) {
      setCurrentEmotion(emotion);
    }
  }, [emotion, isInteracting]);

  // Blink animation - varied timing
  useEffect(() => {
    const randomBlink = () => {
      const delay = 2000 + Math.random() * 3000;
      blinkProgress.value = withSequence(
        withDelay(delay, withTiming(1, { duration: 100 })),
        withTiming(0, { duration: 100 }),
        withDelay(200, withTiming(1, { duration: 100 })),
        withTiming(0, { duration: 100 })
      );
    };
    
    blinkProgress.value = withRepeat(
      withSequence(
        withDelay(3000, withTiming(1, { duration: 100 })),
        withTiming(0, { duration: 100 }),
        withDelay(200, withTiming(1, { duration: 100 })),
        withTiming(0, { duration: 100 })
      ),
      -1,
      false
    );
  }, []);

  // Look around animation - realistic and subtle
  useEffect(() => {
    if (currentEmotion === 'curious' || currentEmotion === 'neutral' || currentEmotion === 'thinking') {
      // Slow, natural eye movement
      lookProgress.value = withRepeat(
        withSequence(
          withTiming(0.7, { duration: 1800, easing: Easing.bezier(0.4, 0.0, 0.2, 1) }),
          withDelay(400, withTiming(-0.6, { duration: 2200, easing: Easing.bezier(0.4, 0.0, 0.2, 1) })),
          withTiming(0, { duration: 1600, easing: Easing.bezier(0.4, 0.0, 0.2, 1) }),
          withDelay(800, withTiming(0, { duration: 0 }))
        ),
        -1,
        false
      );
    } else if (currentEmotion === 'excited' || currentEmotion === 'playful') {
      // Quick, energetic eye movement
      lookProgress.value = withRepeat(
        withSequence(
          withTiming(0.8, { duration: 350, easing: Easing.out(Easing.quad) }),
          withTiming(-0.8, { duration: 500, easing: Easing.inOut(Easing.quad) }),
          withTiming(0, { duration: 350, easing: Easing.in(Easing.quad) }),
          withDelay(200, withTiming(0, { duration: 0 }))
        ),
        3,
        false
      );
    } else if (currentEmotion === 'bored') {
      // Very slow, lazy movement
      lookProgress.value = withRepeat(
        withSequence(
          withDelay(1000, withTiming(0.3, { duration: 2500, easing: Easing.inOut(Easing.ease) })),
          withDelay(1500, withTiming(-0.3, { duration: 2500, easing: Easing.inOut(Easing.ease) })),
          withTiming(0, { duration: 2000, easing: Easing.inOut(Easing.ease) }),
          withDelay(2000, withTiming(0, { duration: 0 }))
        ),
        -1,
        false
      );
    } else {
      // Return to center
      lookProgress.value = withTiming(0, { duration: 600, easing: Easing.out(Easing.ease) });
    }
  }, [currentEmotion]);

  // Glow animation when online
  useEffect(() => {
    if (isOnline) {
      glowProgress.value = withRepeat(
        withSequence(
          withTiming(1, { duration: 2000, easing: Easing.inOut(Easing.ease) }),
          withTiming(0, { duration: 2000, easing: Easing.inOut(Easing.ease) })
        ),
        -1,
        false
      );
    } else {
      glowProgress.value = 0;
    }
  }, [isOnline]);

  // Gesture handlers
  const tapGesture = Gesture.Tap()
    .onEnd(() => {
      runOnJS(handleTouch)();
    });

  const longPressGesture = Gesture.LongPress()
    .minDuration(500)
    .onEnd(() => {
      runOnJS(handleLongPress)();
    });

  const composedGestures = Gesture.Race(longPressGesture, tapGesture);

  const getEyeConfig = () => {
    switch (currentEmotion) {
      case 'happy':
        return { style: 'normal' as EyeStyle, scaleY: 0.65, rotation: 0, pupilSize: 30, lidCurve: 'smile' }; // Squinted happy
      case 'excited':
        return { style: 'normal' as EyeStyle, scaleY: 1.35, rotation: 0, pupilSize: 38, lidCurve: 'normal' }; // Wide eyes
      case 'curious':
        return { style: 'normal' as EyeStyle, scaleY: 1.15, rotation: 0, pupilSize: 34, lidCurve: 'raised' }; // Slightly raised
      case 'thinking':
        return { style: 'normal' as EyeStyle, scaleY: 0.85, rotation: 0, pupilSize: 28, lidCurve: 'normal' }; // Slightly narrowed
      case 'love':
        return { style: 'normal' as EyeStyle, scaleY: 0.7, rotation: 0, pupilSize: 32, lidCurve: 'smile' }; // Soft squint
      case 'sleepy':
        return { style: 'normal' as EyeStyle, scaleY: 0.25, rotation: 0, pupilSize: 24, lidCurve: 'normal' }; // Almost closed
      case 'surprised':
        return { style: 'normal' as EyeStyle, scaleY: 1.45, rotation: 0, pupilSize: 42, lidCurve: 'normal' }; // Very wide
      case 'playful':
        return { style: 'normal' as EyeStyle, scaleY: 1.1, rotation: 0, pupilSize: 36, lidCurve: 'raised' }; // Bright and alert
      case 'bored':
        return { style: 'normal' as EyeStyle, scaleY: 0.8, rotation: 0, pupilSize: 26, lidCurve: 'droopy' }; // Half-lidded
      case 'confused':
        return { style: 'normal' as EyeStyle, scaleY: 1.0, rotation: 3, pupilSize: 32, lidCurve: 'asymmetric' }; // Slight tilt
      default:
        return { style: 'normal' as EyeStyle, scaleY: 1.0, rotation: 0, pupilSize: 32, lidCurve: 'normal' };
    }
  };

  const eyeConfig = getEyeConfig();

  const containerStyle = useAnimatedStyle(() => {
    return {
      transform: [
        { scale: scaleValue.value * heartBeatScale.value },
        { translateY: bounceValue.value },
        { rotate: `${wiggleValue.value}deg` },
      ],
    };
  });

  const leftEyeStyle = useAnimatedStyle(() => {
    const blinkScale = interpolate(blinkProgress.value, [0, 1], [1, 0.1]);
    const lookX = interpolate(lookProgress.value, [-1, 0, 1], [-10, 0, 10]);
    const lookY = currentEmotion === 'curious' ? -5 : currentEmotion === 'sleepy' ? 6 : currentEmotion === 'bored' ? 5 : 0;

    return {
      transform: [
        { translateX: lookX },
        { translateY: lookY },
        { scaleY: blinkScale * eyeConfig.scaleY },
        { rotate: `${eyeConfig.rotation}deg` },
      ],
    };
  });

  const rightEyeStyle = useAnimatedStyle(() => {
    const blinkScale = interpolate(blinkProgress.value, [0, 1], [1, 0.1]);
    const lookX = interpolate(lookProgress.value, [-1, 0, 1], [-10, 0, 10]);
    const lookY = currentEmotion === 'curious' ? -5 : currentEmotion === 'sleepy' ? 6 : currentEmotion === 'bored' ? 5 : 0;

    return {
      transform: [
        { translateX: lookX },
        { translateY: lookY },
        { scaleY: blinkScale * eyeConfig.scaleY },
        { rotate: `${-eyeConfig.rotation}deg` }, // Mirror rotation for right eye
      ],
    };
  });

  const glowStyle = useAnimatedStyle(() => {
    const opacity = interpolate(glowProgress.value, [0, 1], [0.3, 0.8]);
    return {
      opacity: isOnline ? opacity : 0.2,
    };
  });

  const pupilStyle = useAnimatedStyle(() => {
    const lookX = interpolate(lookProgress.value, [-1, 0, 1], [-8, 0, 8]);
    const lookY = currentEmotion === 'curious' ? -5 : currentEmotion === 'sleepy' ? 6 : currentEmotion === 'bored' ? 5 : 0;
    
    return {
      transform: [
        { translateX: lookX },
        { translateY: lookY },
      ],
    };
  });

  const eyeColor = isOnline ? '#34D399' : '#EF4444';
  const glowColor = isOnline ? 'rgba(52, 211, 153, 0.5)' : 'rgba(239, 68, 68, 0.5)';

  const renderEyeContent = () => {
    // Always render realistic pupils, no custom shapes
    return (
      <Animated.View style={pupilStyle}>
        <View style={[styles.pupil, { 
          backgroundColor: eyeColor,
          width: eyeConfig.pupilSize,
          height: eyeConfig.pupilSize,
          borderRadius: eyeConfig.pupilSize / 2,
        }]}>
          <View style={[styles.highlight, {
            width: eyeConfig.pupilSize * 0.3,
            height: eyeConfig.pupilSize * 0.3,
            borderRadius: eyeConfig.pupilSize * 0.15,
          }]} />
          {/* Add subtle inner glow for depth */}
          <View style={[styles.innerGlow, {
            width: eyeConfig.pupilSize * 0.85,
            height: eyeConfig.pupilSize * 0.85,
            borderRadius: eyeConfig.pupilSize * 0.425,
          }]} />
        </View>
      </Animated.View>
    );
  };

  return (
    <GestureDetector gesture={composedGestures}>
      <Animated.View style={[styles.container, containerStyle]}>
        {/* Glow effect */}
        <Animated.View style={[styles.glowContainer, glowStyle]}>
          <View style={[styles.glow, { backgroundColor: glowColor }]} />
        </Animated.View>

        {/* Eyes container */}
        <View style={styles.eyesContainer}>
          {/* Left Eye */}
          <Animated.View style={[styles.eyeOuter, leftEyeStyle]}>
            <View style={styles.eyeWhite}>
              {renderEyeContent()}
            </View>
          </Animated.View>

          {/* Right Eye */}
          <Animated.View style={[styles.eyeOuter, rightEyeStyle]}>
            <View style={styles.eyeWhite}>
              {renderEyeContent()}
            </View>
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
    minHeight: 180,
  },
  glowContainer: {
    position: 'absolute',
    width: '100%',
    height: '100%',
    alignItems: 'center',
    justifyContent: 'center',
  },
  glow: {
    width: 280,
    height: 140,
    borderRadius: 70,
    opacity: 0.3,
  },
  eyesContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 60,
  },
  eyeOuter: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  eyeWhite: {
    width: 70,
    height: 70,
    backgroundColor: '#F9FAFB',
    borderRadius: 35,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.4,
    shadowRadius: 12,
    elevation: 8,
    overflow: 'hidden',
  },
  pupil: {
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.5,
    shadowRadius: 6,
    elevation: 5,
  },
  highlight: {
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    position: 'absolute',
    top: '15%',
    left: '20%',
  },
  innerGlow: {
    position: 'absolute',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.2)',
  },
});

