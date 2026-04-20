import React, { useEffect } from 'react';
import { StyleSheet, View } from 'react-native';
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withSequence,
  withTiming,
} from 'react-native-reanimated';

interface SkeletonProps {
  width?: number | string;
  height?: number;
  borderRadius?: number;
  style?: any;
}

export function Skeleton({ width = '100%', height = 20, borderRadius = 8, style }: SkeletonProps) {
  const opacity = useSharedValue(0.3);

  useEffect(() => {
    opacity.value = withRepeat(
      withSequence(
        withTiming(0.6, { duration: 800 }),
        withTiming(0.3, { duration: 800 })
      ),
      -1,
      false
    );
  }, []);

  const animatedStyle = useAnimatedStyle(() => ({
    opacity: opacity.value,
  }));

  return (
    <Animated.View
      style={[
        styles.skeleton,
        {
          width,
          height,
          borderRadius,
        },
        animatedStyle,
        style,
      ]}
    />
  );
}

export function FeatureCardSkeleton() {
  return (
    <View style={styles.featureCard}>
      <Skeleton width={40} height={40} borderRadius={10} />
      <Skeleton width="80%" height={16} style={{ marginTop: 8 }} />
      <Skeleton width="100%" height={12} style={{ marginTop: 4 }} />
    </View>
  );
}

export function StatusCardSkeleton() {
  return (
    <View style={styles.statusCard}>
      <Skeleton width={48} height={48} borderRadius={12} />
      <View style={{ flex: 1 }}>
        <Skeleton width="40%" height={14} />
        <Skeleton width="60%" height={18} style={{ marginTop: 6 }} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  skeleton: {
    backgroundColor: 'rgba(55, 55, 55, 0.5)',
  },
  featureCard: {
    width: '31.5%',
    backgroundColor: 'rgba(26, 26, 26, 0.7)',
    padding: 14,
    borderWidth: 1,
    borderColor: 'rgba(37, 37, 37, 0.6)',
    borderRadius: 12,
  },
  statusCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
    padding: 16,
    backgroundColor: 'rgba(26, 26, 26, 0.7)',
    borderWidth: 1,
    borderColor: 'rgba(37, 37, 37, 0.6)',
    borderRadius: 12,
  },
});

