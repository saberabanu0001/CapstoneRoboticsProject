import React, { useEffect, useState } from 'react';
import { StyleSheet, Pressable, View } from 'react-native';
import Svg, { Circle, Ellipse, G, Defs, RadialGradient, Stop, Path } from 'react-native-svg';
import Animated, {
  useSharedValue,
  useAnimatedProps,
  withTiming,
  withRepeat,
  withSequence,
  withSpring,
  Easing,
  interpolate,
  runOnJS,
} from 'react-native-reanimated';
import { DeviceMotion } from 'expo-sensors';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';

const AnimatedCircle = Animated.createAnimatedComponent(Circle);
const AnimatedEllipse = Animated.createAnimatedComponent(Ellipse);
const AnimatedG = Animated.createAnimatedComponent(G);
const AnimatedPath = Animated.createAnimatedComponent(Path);

type Emotion = 'happy' | 'excited' | 'curious' | 'thinking' | 'neutral' | 'love' | 'sleepy' | 'surprised' | 'bored' | 'hurt';

interface RobotEyesProps {
  emotion?: Emotion;
  isOnline?: boolean;
}

export function RobotEyes({ emotion = 'neutral', isOnline = true }: RobotEyesProps) {
  const [currentEmotion, setCurrentEmotion] = useState<Emotion>(emotion);
  const [lastTapTime, setLastTapTime] = useState(0);
  const [lastInteractionTime, setLastInteractionTime] = useState(Date.now());
  const [isPanning, setIsPanning] = useState(false);
  
  // Animation values
  const blinkProgress = useSharedValue(0);
  const lookX = useSharedValue(0);
  const lookY = useSharedValue(0);
  const pupilScale = useSharedValue(1);
  const eyeHeight = useSharedValue(40);
  const containerScale = useSharedValue(1);
  const wiggle = useSharedValue(0);
  const panX = useSharedValue(0);
  const panY = useSharedValue(0);

  // Get eye config - more subtle
  const getEyeConfig = () => {
    switch (currentEmotion) {
      case 'happy': return { height: 48, pupilScale: 1.0, lookSpeed: 2.0, style: 'normal' };
      case 'excited': return { height: 55, pupilScale: 1.05, lookSpeed: 1.8, style: 'normal' };
      case 'curious': return { height: 55, pupilScale: 1.0, lookSpeed: 2.0, style: 'normal' };
      case 'thinking': return { height: 48, pupilScale: 1.0, lookSpeed: 2.5, style: 'normal' };
      case 'love': return { height: 50, pupilScale: 1.0, lookSpeed: 2.2, style: 'heart' };
      case 'sleepy': return { height: 25, pupilScale: 0.9, lookSpeed: 3.5, style: 'normal' };
      case 'surprised': return { height: 58, pupilScale: 1.08, lookSpeed: 1.5, style: 'normal' };
      case 'bored': return { height: 45, pupilScale: 0.95, lookSpeed: 3.0, style: 'normal' };
      case 'hurt': return { height: 35, pupilScale: 0.9, lookSpeed: 0, style: 'hurt' }; // >< eyes
      default: return { height: 55, pupilScale: 1.0, lookSpeed: 2.0, style: 'normal' };
    }
  };

  const eyeConfig = getEyeConfig();

  // Update emotion
  useEffect(() => {
    setCurrentEmotion(emotion);
  }, [emotion]);

  // Animate to emotion - smooth transitions
  useEffect(() => {
    const config = getEyeConfig();
    eyeHeight.value = withTiming(config.height, { 
      duration: 600, 
      easing: Easing.out(Easing.cubic) 
    });
    pupilScale.value = withTiming(config.pupilScale, { 
      duration: 600,
      easing: Easing.out(Easing.cubic)
    });
  }, [currentEmotion]);

  // Blinking
  useEffect(() => {
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

  // Eye movement - smooth and natural (pause during panning)
  useEffect(() => {
    if (isPanning) {
      // Stop automatic movement while panning
      return;
    }
    
    const duration = eyeConfig.lookSpeed * 1000;
    
    if (eyeConfig.lookSpeed === 0) {
      // No movement for certain emotions (like hurt)
      lookX.value = 0;
      lookY.value = 0;
      return;
    }
    
    lookX.value = withRepeat(
      withSequence(
        withTiming(12, { duration, easing: Easing.bezier(0.4, 0, 0.2, 1) }),
        withTiming(-10, { duration: duration * 1.5, easing: Easing.bezier(0.4, 0, 0.2, 1) }),
        withTiming(0, { duration, easing: Easing.bezier(0.4, 0, 0.2, 1) })
      ),
      -1,
      false
    );

    lookY.value = withRepeat(
      withSequence(
        withTiming(0, { duration: duration * 1.5 }),
        withTiming(-6, { duration, easing: Easing.bezier(0.4, 0, 0.2, 1) }),
        withTiming(4, { duration: duration * 1.2, easing: Easing.bezier(0.4, 0, 0.2, 1) }),
        withTiming(0, { duration })
      ),
      -1,
      false
    );
  }, [currentEmotion, isPanning]);

  // Motion detection
  useEffect(() => {
    DeviceMotion.setUpdateInterval(100);
    let shakeIntensities: number[] = [];
    let lastShakeTime = 0;
    
    const subscription = DeviceMotion.addListener((motionData) => {
      const { acceleration } = motionData;
      
      if (acceleration) {
        const magnitude = Math.sqrt(
          (acceleration.x || 0) ** 2 + 
          (acceleration.y || 0) ** 2 + 
          (acceleration.z || 0) ** 2
        );
        
        const now = Date.now();
        
        if (magnitude > 3.0) {
          shakeIntensities.push(magnitude);
          shakeIntensities = shakeIntensities.filter(() => now - lastShakeTime < 200);
          
          if (shakeIntensities.length >= 3) {
            const avgIntensity = shakeIntensities.reduce((a, b) => a + b, 0) / shakeIntensities.length;
            
            if (avgIntensity > 3.5 && now - lastShakeTime > 800) {
              lastShakeTime = now;
              shakeIntensities = [];
              runOnJS(handleShake)();
            }
          }
        }
      }
    });

    return () => subscription.remove();
  }, []);

  const handleShake = () => {
    setLastInteractionTime(Date.now());
    setCurrentEmotion('surprised');
    setTimeout(() => setCurrentEmotion(emotion), 1500);
  };

  const handlePress = () => {
    const now = Date.now();
    setLastInteractionTime(now);
    
    if (now - lastTapTime < 400) {
      // Double tap - show pain/hurt >< eyes
      setCurrentEmotion('hurt');
      setTimeout(() => setCurrentEmotion(emotion), 1500);
    } else {
      // Single tap - subtle response
      setCurrentEmotion('curious');
      setTimeout(() => setCurrentEmotion(emotion), 1000);
    }
    
    setLastTapTime(now);
  };

  const handleLongPress = () => {
    setLastInteractionTime(Date.now());
    // Long press/petting - show love with heart eyes
    setCurrentEmotion('love');
    setTimeout(() => setCurrentEmotion(emotion), 2500);
  };

  // Boredom detection
  useEffect(() => {
    const checkBoredom = setInterval(() => {
      const timeSinceInteraction = Date.now() - lastInteractionTime;
      
      if (!isPanning && currentEmotion !== 'sleepy' && currentEmotion !== 'bored') {
        if (timeSinceInteraction > 30000) { // 30 seconds
          setCurrentEmotion('bored');
        }
      }
    }, 5000);
    
    return () => clearInterval(checkBoredom);
  }, [lastInteractionTime, isPanning, currentEmotion]);

  // Animated props for eyes
  const leftEyeProps = useAnimatedProps(() => {
    const blinkHeight = interpolate(blinkProgress.value, [0, 1], [eyeHeight.value, 2]);
    return {
      ry: blinkHeight / 2,
    };
  });

  const rightEyeProps = useAnimatedProps(() => {
    const blinkHeight = interpolate(blinkProgress.value, [0, 1], [eyeHeight.value, 2]);
    return {
      ry: blinkHeight / 2,
    };
  });

  const leftPupilProps = useAnimatedProps(() => {
    const blinkOpacity = interpolate(blinkProgress.value, [0, 0.5, 1], [1, 0.3, 0]); // Fade during blink
    // Use pan if active, otherwise use automatic look
    const finalX = panX.value !== 0 ? panX.value : lookX.value;
    const finalY = panY.value !== 0 ? panY.value : lookY.value;
    return {
      cx: 75 + finalX,
      cy: 75 + finalY,
      r: 22 * pupilScale.value,
      opacity: blinkOpacity,
    };
  });

  const rightPupilProps = useAnimatedProps(() => {
    const blinkOpacity = interpolate(blinkProgress.value, [0, 0.5, 1], [1, 0.3, 0]); // Fade during blink
    // Use pan if active, otherwise use automatic look
    const finalX = panX.value !== 0 ? panX.value : lookX.value;
    const finalY = panY.value !== 0 ? panY.value : lookY.value;
    return {
      cx: 225 + finalX,
      cy: 75 + finalY,
      r: 22 * pupilScale.value,
      opacity: blinkOpacity,
    };
  });

  // Highlight props - move with pupil
  const leftHighlightProps = useAnimatedProps(() => {
    const blinkOpacity = interpolate(blinkProgress.value, [0, 0.5, 1], [1, 0.3, 0]);
    const finalX = panX.value !== 0 ? panX.value : lookX.value;
    const finalY = panY.value !== 0 ? panY.value : lookY.value;
    return {
      cx: 75 + finalX + 6,
      cy: 75 + finalY - 6,
      opacity: blinkOpacity,
    };
  });

  const rightHighlightProps = useAnimatedProps(() => {
    const blinkOpacity = interpolate(blinkProgress.value, [0, 0.5, 1], [1, 0.3, 0]);
    const finalX = panX.value !== 0 ? panX.value : lookX.value;
    const finalY = panY.value !== 0 ? panY.value : lookY.value;
    return {
      cx: 225 + finalX + 6,
      cy: 75 + finalY - 6,
      opacity: blinkOpacity,
    };
  });

  // Animated props for heart eyes opacity
  const leftHeartProps = useAnimatedProps(() => {
    const blinkOpacity = interpolate(blinkProgress.value, [0, 0.5, 1], [1, 0.3, 0]);
    return {
      opacity: blinkOpacity,
    };
  });

  const rightHeartProps = useAnimatedProps(() => {
    const blinkOpacity = interpolate(blinkProgress.value, [0, 0.5, 1], [1, 0.3, 0]);
    return {
      opacity: blinkOpacity,
    };
  });

  const containerProps = useAnimatedProps(() => ({
    // No transform - keep it simple and realistic
  }));

  // Gestures
  const tapGesture = Gesture.Tap().onEnd(() => {
    'worklet';
    runOnJS(handlePress)();
  });

  const longPressGesture = Gesture.LongPress().minDuration(500).onEnd(() => {
    'worklet';
    runOnJS(handleLongPress)();
  });

  const panGesture = Gesture.Pan()
    .onBegin(() => {
      'worklet';
      runOnJS(setIsPanning)(true);
      runOnJS(setLastInteractionTime)(Date.now());
    })
    .onUpdate((event) => {
      'worklet';
      // Map pan movement to eye position (within bounds)
      panX.value = Math.max(-15, Math.min(15, event.translationX / 10));
      panY.value = Math.max(-10, Math.min(10, event.translationY / 10));
    })
    .onEnd(() => {
      'worklet';
      // Smoothly return to center
      panX.value = withTiming(0, { duration: 600, easing: Easing.out(Easing.ease) });
      panY.value = withTiming(0, { duration: 600, easing: Easing.out(Easing.ease) });
      runOnJS(setIsPanning)(false);
    });

  const composedGestures = Gesture.Exclusive(
    panGesture,
    Gesture.Race(longPressGesture, tapGesture)
  );

  const eyeColor = isOnline ? '#34D399' : '#EF4444';

  return (
    <GestureDetector gesture={composedGestures}>
      <View style={styles.container}>
      <Animated.View style={[styles.svgContainer, containerProps as any]}>
        <Svg width="300" height="150" viewBox="0 0 300 150">
          <Defs>
            <RadialGradient id="eyeGlow" cx="50%" cy="50%" r="50%">
              <Stop offset="0%" stopColor={eyeColor} stopOpacity="0.15" />
              <Stop offset="100%" stopColor={eyeColor} stopOpacity="0" />
            </RadialGradient>
            <RadialGradient id="pupilGrad" cx="35%" cy="35%">
              <Stop offset="0%" stopColor={eyeColor} stopOpacity="1" />
              <Stop offset="100%" stopColor={eyeColor} stopOpacity="0.85" />
            </RadialGradient>
          </Defs>

          {/* Glow effect */}
          {eyeConfig.style !== 'hurt' && <Circle cx="75" cy="75" r="65" fill="url(#eyeGlow)" />}
          {eyeConfig.style !== 'hurt' && <Circle cx="225" cy="75" r="65" fill="url(#eyeGlow)" />}

          {/* Left Eye */}
          <G>
            {/* Eye white */}
            <AnimatedEllipse
              cx="75"
              cy="75"
              rx="50"
              animatedProps={leftEyeProps}
              fill="#F9FAFB"
              stroke="#D1D5DB"
              strokeWidth="1.5"
            />
            {/* Render based on style */}
            {eyeConfig.style === 'heart' ? (
              // Heart-shaped pupil
              <AnimatedPath
                d="M 75,85 C 75,85 60,73 60,65 C 60,58 65,55 70,55 C 73,55 75,57 75,57 C 75,57 77,55 80,55 C 85,55 90,58 90,65 C 90,73 75,85 75,85 Z"
                fill="#FF6B9D"
                animatedProps={leftHeartProps}
              />
            ) : eyeConfig.style === 'hurt' ? (
              // > hurt eye (right angle only for left eye)
              <Ellipse cx="75" cy="75" rx="25" ry="5" fill="#EF4444" opacity="0.8" transform="rotate(20 75 75)" />
            ) : (
              // Normal pupil
              <>
                <AnimatedCircle
                  animatedProps={leftPupilProps}
                  fill="url(#pupilGrad)"
                />
                {/* Highlight - moves with pupil */}
                <AnimatedCircle
                  animatedProps={leftHighlightProps}
                  r="7"
                  fill="rgba(255,255,255,0.9)"
                />
              </>
            )}
          </G>

          {/* Right Eye */}
          <G>
            {/* Eye white */}
            <AnimatedEllipse
              cx="225"
              cy="75"
              rx="50"
              animatedProps={rightEyeProps}
              fill="#F9FAFB"
              stroke="#D1D5DB"
              strokeWidth="1.5"
            />
            {/* Render based on style */}
            {eyeConfig.style === 'heart' ? (
              // Heart-shaped pupil
              <AnimatedPath
                d="M 225,85 C 225,85 210,73 210,65 C 210,58 215,55 220,55 C 223,55 225,57 225,57 C 225,57 227,55 230,55 C 235,55 240,58 240,65 C 240,73 225,85 225,85 Z"
                fill="#FF6B9D"
                animatedProps={rightHeartProps}
              />
            ) : eyeConfig.style === 'hurt' ? (
              // < hurt eye (left angle only for right eye)
              <Ellipse cx="225" cy="75" rx="25" ry="5" fill="#EF4444" opacity="0.8" transform="rotate(-20 225 75)" />
            ) : (
              // Normal pupil
              <>
                <AnimatedCircle
                  animatedProps={rightPupilProps}
                  fill="url(#pupilGrad)"
                />
                {/* Highlight - moves with pupil */}
                <AnimatedCircle
                  animatedProps={rightHighlightProps}
                  r="7"
                  fill="rgba(255,255,255,0.9)"
                />
              </>
            )}
          </G>
        </Svg>
      </Animated.View>
    </View>
    </GestureDetector>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 30,
    paddingHorizontal: 20,
  },
  svgContainer: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.15,
    shadowRadius: 6,
    elevation: 3,
  },
});

