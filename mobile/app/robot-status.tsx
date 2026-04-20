import React, { useMemo, useEffect } from 'react';
import { Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { useRouter } from 'expo-router';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { IconSymbol } from '@/components/ui/icon-symbol';
import { useRobot } from '@/context/robot-provider';

interface StatusItem {
  label: string;
  value: string;
  icon: string;
  color: string;
}

export default function RobotStatusScreen() {
  const router = useRouter();
  const { status } = useRobot();

  // Debug: Log status to see what we're getting
  useEffect(() => {
    if (status) {
      console.log('Robot Status Debug:', {
        battery: status.battery,
        telemetry: status.telemetry,
        health: status.health,
        telemetryBattery: status.telemetry?.battery,
        healthBattery: status.health?.battery,
      });
    }
  }, [status]);

  // Check for battery in multiple possible fields (API returns battery_percent)
  const batteryRaw = status?.battery 
    ?? status?.telemetry?.battery_percent 
    ?? status?.telemetry?.battery 
    ?? status?.health?.battery;
  const batteryLevel = typeof batteryRaw === 'number' ? Math.round(batteryRaw) : undefined;
  const batteryColor = batteryLevel === undefined
    ? '#67686C'
    : batteryLevel >= 60
      ? '#34D399'
      : batteryLevel >= 30
        ? '#FBBF24'
        : '#EF4444';

  const isOnline = Boolean(status?.network?.ip);
  const wifiSsid = status?.network?.wifiSsid ?? status?.network?.ssid ?? 'Not connected';
  const ipAddress = status?.network?.ip ?? 'No IP';

  const statusItems: StatusItem[] = useMemo(() => [
    {
      label: 'Battery',
      value: batteryLevel !== undefined ? `${batteryLevel}%` : 'Unknown',
      icon: 'battery.75',
      color: batteryColor,
    },
    {
      label: 'WiFi Network',
      value: wifiSsid,
      icon: 'wifi',
      color: isOnline ? '#34D399' : '#67686C',
    },
    {
      label: 'IP Address',
      value: ipAddress,
      icon: 'network',
      color: '#3B82F6',
    },
    {
      label: 'Connection',
      value: isOnline ? 'Online' : 'Offline',
      icon: 'antenna.radiowaves.left.and.right',
      color: isOnline ? '#34D399' : '#EF4444',
    },
  ], [batteryLevel, batteryColor, wifiSsid, ipAddress, isOnline]);

  const systemInfo = useMemo(() => [
    { label: 'Platform', value: 'Raspberry Pi 5' },
    { label: 'Camera', value: 'OAK-D Stereo' },
    { label: 'LIDAR', value: 'RPLidar C1' },
    { label: 'Base', value: 'Waveshare UGV' },
  ], []);

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <ScrollView 
        contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}
      >
        <ThemedView style={styles.container}>
          <Animated.View 
            entering={FadeInDown.duration(400)}
            style={styles.headerRow}
          >
            <Pressable style={styles.backButton} onPress={() => router.back()}>
              <IconSymbol name="chevron.left" size={16} color="#E5E7EB" />
            </Pressable>
            <ThemedText type="title">Robot Status</ThemedText>
          </Animated.View>

          <Animated.View entering={FadeInDown.delay(50).duration(400)}>
            <ThemedText style={styles.description}>
              Real-time telemetry and system information
            </ThemedText>
          </Animated.View>

          {/* Live Status Grid */}
          <Animated.View 
            entering={FadeInDown.delay(100).duration(400)}
            style={styles.section}
          >
            <ThemedText style={styles.sectionTitle}>LIVE TELEMETRY</ThemedText>
            <View style={styles.statusGrid}>
              {statusItems.map((item, index) => (
                <Animated.View 
                  key={item.label}
                  entering={FadeInDown.delay(150 + index * 50).duration(400)}
                  style={styles.statusCard}
                >
                  <View style={[styles.statusIconContainer, { backgroundColor: `${item.color}20` }]}>
                    <IconSymbol name={item.icon} size={24} color={item.color} />
                  </View>
                  <View style={styles.statusInfo}>
                    <ThemedText style={styles.statusLabel}>{item.label}</ThemedText>
                    <ThemedText style={styles.statusValue}>{item.value}</ThemedText>
                  </View>
                </Animated.View>
              ))}
            </View>
          </Animated.View>

          {/* System Info */}
          <Animated.View 
            entering={FadeInDown.delay(400).duration(400)}
            style={styles.section}
          >
            <ThemedText style={styles.sectionTitle}>HARDWARE</ThemedText>
            <ThemedView style={styles.infoCard}>
              {systemInfo.map((info, index) => (
                <View key={info.label} style={styles.infoRow}>
                  <ThemedText style={styles.infoLabel}>{info.label}</ThemedText>
                  <ThemedText style={styles.infoValue}>{info.value}</ThemedText>
                </View>
              ))}
            </ThemedView>
          </Animated.View>

          {/* Capabilities */}
          <Animated.View 
            entering={FadeInDown.delay(500).duration(400)}
            style={styles.section}
          >
            <ThemedText style={styles.sectionTitle}>ACTIVE FEATURES</ThemedText>
            <View style={styles.capabilitiesGrid}>
              {[
                { label: 'Voice Control', icon: 'mic.fill', active: true },
                { label: 'Face Recognition', icon: 'person.crop.rectangle', active: true },
                { label: 'Depth Vision', icon: 'camera.fill', active: true },
                { label: 'Navigation', icon: 'location.fill', active: false },
                { label: 'SLAM Mapping', icon: 'map.fill', active: false },
                { label: 'Object Detection', icon: 'viewfinder', active: true },
              ].map((cap, index) => (
                <Animated.View 
                  key={cap.label}
                  entering={FadeInDown.delay(550 + index * 40).duration(300)}
                  style={styles.capabilityChip}
                >
                  <IconSymbol 
                    name={cap.icon} 
                    size={16} 
                    color={cap.active ? '#1DD1A1' : '#67686C'} 
                  />
                  <ThemedText style={[
                    styles.capabilityText,
                    { color: cap.active ? '#E5E7EB' : '#67686C' }
                  ]}>
                    {cap.label}
                  </ThemedText>
                </Animated.View>
              ))}
            </View>
          </Animated.View>
        </ThemedView>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#0F0F0F',
  },
  scroll: {
    flexGrow: 1,
    paddingBottom: 40,
  },
  container: {
    flex: 1,
    padding: 20,
    gap: 24,
    backgroundColor: '#0F0F0F',
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
  description: {
    color: '#9CA3AF',
    marginTop: 6,
    fontSize: 14,
  },
  section: {
    gap: 12,
  },
  sectionTitle: {
    fontSize: 12,
    fontFamily: 'JetBrainsMono_600SemiBold',
    color: '#67686C',
    textTransform: 'uppercase',
    letterSpacing: 1.2,
  },
  statusGrid: {
    gap: 12,
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
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 2,
  },
  statusIconContainer: {
    width: 48,
    height: 48,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  statusInfo: {
    flex: 1,
  },
  statusLabel: {
    fontSize: 13,
    color: '#9CA3AF',
    marginBottom: 2,
  },
  statusValue: {
    fontSize: 18,
    fontFamily: 'JetBrainsMono_600SemiBold',
    color: '#F9FAFB',
  },
  infoCard: {
    padding: 16,
    backgroundColor: 'rgba(26, 26, 26, 0.7)',
    borderWidth: 1,
    borderColor: 'rgba(37, 37, 37, 0.6)',
    borderRadius: 12,
    gap: 12,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: 'rgba(55, 55, 55, 0.4)',
  },
  infoLabel: {
    fontSize: 14,
    color: '#9CA3AF',
  },
  infoValue: {
    fontSize: 14,
    fontFamily: 'JetBrainsMono_600SemiBold',
    color: '#E5E7EB',
  },
  capabilitiesGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  capabilityChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    backgroundColor: 'rgba(26, 26, 26, 0.7)',
    borderWidth: 1,
    borderColor: 'rgba(37, 37, 37, 0.6)',
    borderRadius: 20,
  },
  capabilityText: {
    fontSize: 13,
    fontFamily: 'JetBrainsMono_600SemiBold',
  },
});

