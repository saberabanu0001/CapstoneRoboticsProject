import { useRouter } from 'expo-router';
import React, { useEffect } from 'react';
import { Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Animated, { 
  useSharedValue, 
  useAnimatedStyle, 
  withRepeat, 
  withSequence,
  withTiming,
  FadeInDown,
  FadeIn
} from 'react-native-reanimated';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { IconSymbol } from '@/components/ui/icon-symbol';
import { RobotEyes } from '@/components/robot-eyes-svg';
import { useRobot } from '@/context/robot-provider';

const PRIMARY_ACTIONS = [
  {
    id: 'voice',
    label: 'Voice Chat',
    description: 'Talk with AI',
    href: '/agentic' as const,
    icon: 'mic.fill' as const,
    gradient: ['#1DD1A1', '#17B891'],
  },
  {
    id: 'drive',
    label: 'Manual Drive',
    description: 'Take control',
    href: '/manual' as const,
    icon: 'gamecontroller.fill' as const,
    gradient: ['#3B82F6', '#2563EB'],
  },
] as const;

const SECONDARY_ACTIONS = [
  {
    id: 'status',
    label: 'Status',
    icon: 'chart.bar.fill' as const,
    href: '/robot-status' as const,
  },
  {
    id: 'settings',
    label: 'Settings',
    icon: 'gearshape.fill' as const,
    href: '/(tabs)/settings' as const,
  },
] as const;

export default function HomeScreen() {
  const { status } = useRobot();
  const router = useRouter();

  const batteryRaw = status?.battery ?? status?.telemetry?.battery ?? status?.health?.battery;
  const batteryLevel = typeof batteryRaw === 'number' ? Math.round(batteryRaw) : undefined;
  const batteryLabel = batteryLevel !== undefined ? `${batteryLevel}%` : '—';
  const batteryColor = batteryLevel === undefined
    ? '#67686C'
    : batteryLevel >= 60
      ? '#34D399'
      : batteryLevel >= 30
        ? '#FBBF24'
        : '#EF4444';

  const isOnline = Boolean(status?.network?.ip);
  const wifiLabel = status?.network?.wifiSsid ?? status?.network?.ssid ?? (isOnline ? 'Connected' : 'Offline');

  // Animated pulse for status dot
  const pulseScale = useSharedValue(1);
  
  useEffect(() => {
    if (isOnline) {
      pulseScale.value = withRepeat(
        withSequence(
          withTiming(1.2, { duration: 1000 }),
          withTiming(1, { duration: 1000 })
        ),
        -1,
        false
      );
    }
  }, [isOnline]);

  const pulseStyle = useAnimatedStyle(() => ({
    transform: [{ scale: pulseScale.value }],
  }));

  // Determine robot emotion based on status
  const getEmotion = () => {
    if (!isOnline) return 'neutral';
    if (batteryLevel !== undefined && batteryLevel < 20) return 'thinking';
    if (batteryLevel !== undefined && batteryLevel > 80) return 'happy';
    return 'curious';
  };

  return (
    <SafeAreaView style={styles.safeArea} edges={["top"]}>
      <ThemedView style={styles.screen}>
        <ScrollView
          contentContainerStyle={styles.content}
          showsVerticalScrollIndicator={false}
        >
          {/* Animated Robot Eyes */}
          <Animated.View entering={FadeIn.duration(800)}>
            <RobotEyes emotion={getEmotion()} isOnline={isOnline} />
          </Animated.View>

          {/* Status Section */}
          <Animated.View 
            entering={FadeIn.duration(600)}
            style={styles.statusSection}
          >
            <View style={styles.inlineStatus}>
              <View style={styles.statusChip}>
                <Animated.View 
                  style={[
                    styles.statusIndicator,
                    { backgroundColor: isOnline ? '#34D399' : '#EF4444' },
                    isOnline && pulseStyle
                  ]}
                />
                <ThemedText style={styles.statusChipText}>
                  {isOnline ? 'Online' : 'Offline'}
                </ThemedText>
              </View>
              <View style={styles.statusChip}>
                <IconSymbol name="battery.75" color={batteryColor} size={14} />
                <ThemedText style={styles.statusChipText}>{batteryLabel}</ThemedText>
              </View>
            </View>
          </Animated.View>

          {/* Primary Actions - Big Cards */}
          <Animated.View 
            entering={FadeInDown.delay(200).duration(500)}
            style={styles.primarySection}
          >
            {PRIMARY_ACTIONS.map((action, index) => (
              <Animated.View 
                key={action.id}
                entering={FadeInDown.delay(300 + index * 100).duration(500)}
              >
                <Pressable
                  style={({ pressed }) => [
                    styles.primaryCard,
                    pressed && styles.primaryCardPressed,
                  ]}
                  onPress={() => router.push(action.href)}
                >
                  <View style={styles.primaryCardContent}>
                    <View style={[styles.primaryIconContainer, { backgroundColor: action.gradient[0] }]}>
                      <IconSymbol name={action.icon} size={28} color="#FFFFFF" />
                    </View>
                    <View style={styles.primaryTextContainer}>
                      <ThemedText style={styles.primaryLabel}>{action.label}</ThemedText>
                      <ThemedText style={styles.primaryDescription}>{action.description}</ThemedText>
                    </View>
                    <IconSymbol name="chevron.right" size={20} color="#9CA3AF" />
                  </View>
                </Pressable>
              </Animated.View>
            ))}
          </Animated.View>

          {/* Secondary Actions - Compact */}
          <Animated.View 
            entering={FadeInDown.delay(500).duration(500)}
            style={styles.secondarySection}
          >
            {SECONDARY_ACTIONS.map((action, index) => (
              <Animated.View 
                key={action.id}
                entering={FadeInDown.delay(600 + index * 80).duration(400)}
                style={{ flex: 1 }}
              >
                <Pressable
                  style={({ pressed }) => [
                    styles.secondaryCard,
                    pressed && styles.secondaryCardPressed,
                  ]}
                  onPress={() => router.push(action.href)}
                >
                  <IconSymbol name={action.icon} size={24} color="#E5E7EB" />
                  <ThemedText style={styles.secondaryLabel}>{action.label}</ThemedText>
                </Pressable>
              </Animated.View>
            ))}
          </Animated.View>

          {/* System Info - Minimal */}
          {status?.network?.ip && (
            <Animated.View 
              entering={FadeInDown.delay(700).duration(500)}
              style={styles.infoFooter}
            >
              <ThemedText style={styles.infoText}>
                {wifiLabel} • {status.network.ip}
              </ThemedText>
            </Animated.View>
          )}

        </ScrollView>
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
  content: {
    padding: 24,
    paddingTop: 8,
    paddingBottom: 48,
    gap: 24,
  },
  
  // Status Section
  statusSection: {
    gap: 20,
  },
  
  // Inline Status
  inlineStatus: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 12,
  },
  statusChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: 'rgba(26, 26, 26, 0.6)',
    borderWidth: 1,
    borderColor: 'rgba(37, 37, 37, 0.4)',
    borderRadius: 20,
  },
  statusIndicator: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  statusChipText: {
    fontSize: 13,
    color: '#D1D5DB',
    fontFamily: 'JetBrainsMono_500Medium',
  },
  
  // Primary Actions
  primarySection: {
    gap: 16,
  },
  primaryCard: {
    backgroundColor: 'rgba(26, 26, 26, 0.7)',
    borderWidth: 1,
    borderColor: 'rgba(37, 37, 37, 0.6)',
    borderRadius: 16,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 8,
    elevation: 4,
  },
  primaryCardPressed: {
    backgroundColor: 'rgba(34, 34, 34, 0.9)',
    transform: [{ scale: 0.98 }],
  },
  primaryCardContent: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 20,
    gap: 16,
  },
  primaryIconContainer: {
    width: 56,
    height: 56,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 3,
  },
  primaryTextContainer: {
    flex: 1,
    gap: 4,
  },
  primaryLabel: {
    fontSize: 18,
    fontFamily: 'JetBrainsMono_600SemiBold',
    color: '#F9FAFB',
  },
  primaryDescription: {
    fontSize: 14,
    color: '#9CA3AF',
  },
  
  // Secondary Actions
  secondarySection: {
    flexDirection: 'row',
    gap: 16,
  },
  secondaryCard: {
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
    paddingVertical: 24,
    paddingHorizontal: 16,
    backgroundColor: 'rgba(26, 26, 26, 0.6)',
    borderWidth: 1,
    borderColor: 'rgba(37, 37, 37, 0.4)',
    borderRadius: 16,
  },
  secondaryCardPressed: {
    backgroundColor: 'rgba(34, 34, 34, 0.8)',
    transform: [{ scale: 0.97 }],
  },
  secondaryLabel: {
    fontSize: 14,
    fontFamily: 'JetBrainsMono_500Medium',
    color: '#D1D5DB',
  },
  
  // Footer Info
  infoFooter: {
    alignItems: 'center',
    paddingTop: 8,
  },
  infoText: {
    fontSize: 12,
    color: '#67686C',
    fontFamily: 'JetBrainsMono_400Regular',
  },
});
