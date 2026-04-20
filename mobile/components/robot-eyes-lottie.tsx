import React, { useEffect, useRef, useState } from 'react';
import { StyleSheet, View, Pressable } from 'react-native';
import LottieView from 'lottie-react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withSpring,
  withSequence,
  withTiming,
  Easing,
} from 'react-native-reanimated';
import { DeviceMotion } from 'expo-sensors';

interface RobotEyesProps {
  emotion?: string;
  isOnline?: boolean;
}

export function RobotEyes({ emotion = 'neutral', isOnline = true }: RobotEyesProps) {
  const leftEyeRef = useRef<LottieView>(null);
  const rightEyeRef = useRef<LottieView>(null);
  const [lastInteractionTime, setLastInteractionTime] = useState(Date.now());
  const [lastTapTime, setLastTapTime] = useState(0);
  
  const containerScale = useSharedValue(1);
  const wiggle = useSharedValue(0);

  // Play blink animation periodically
  useEffect(() => {
    const blinkInterval = setInterval(() => {
      leftEyeRef.current?.play(0, 30); // Blink frames
      rightEyeRef.current?.play(0, 30);
    }, 3000 + Math.random() * 2000);

    return () => clearInterval(blinkInterval);
  }, []);

  // Motion detection for shake
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
              handleShake();
            }
          }
        }
      }
    });

    return () => subscription.remove();
  }, []);

  const handleShake = () => {
    setLastInteractionTime(Date.now());
    wiggle.value = withSequence(
      withTiming(-10, { duration: 60 }),
      withTiming(10, { duration: 60 }),
      withTiming(-10, { duration: 60 }),
      withTiming(10, { duration: 60 }),
      withTiming(0, { duration: 60 })
    );
  };

  const handlePress = () => {
    const now = Date.now();
    setLastInteractionTime(now);
    
    // Double tap detection
    if (now - lastTapTime < 400) {
      // Double tap - show love
      containerScale.value = withSequence(
        withSpring(1.15, { damping: 6 }),
        withSpring(0.95, { damping: 8 }),
        withSpring(1.1, { damping: 6 }),
        withSpring(1, { damping: 8 })
      );
    } else {
      // Single tap - bounce
      containerScale.value = withSequence(
        withSpring(1.1, { damping: 8 }),
        withSpring(1)
      );
    }
    
    setLastTapTime(now);
  };

  const containerStyle = useAnimatedStyle(() => ({
    transform: [
      { scale: containerScale.value },
      { rotate: `${wiggle.value}deg` }
    ],
  }));

  const eyeColor = isOnline ? '#34D399' : '#EF4444';

  return (
    <Pressable onPress={handlePress}>
      <Animated.View style={[styles.container, containerStyle]}>
        <View style={styles.eyesContainer}>
          {/* Simple SVG-style eyes since we don't have a Lottie file yet */}
          <View style={styles.eyeWhite}>
            <View style={[styles.pupil, { backgroundColor: eyeColor }]}>
              <View style={styles.highlight} />
            </View>
          </View>
          
          <View style={styles.eyeWhite}>
            <View style={[styles.pupil, { backgroundColor: eyeColor }]}>
              <View style={styles.highlight} />
            </View>
          </View>
        </View>
      </Animated.View>
    </Pressable>
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
    width: 40,
    height: 40,
    borderRadius: 20,
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

