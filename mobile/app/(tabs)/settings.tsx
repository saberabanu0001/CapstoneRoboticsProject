import { useRouter } from 'expo-router';
import React, { useCallback, useState, useEffect } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Animated, { FadeInDown } from 'react-native-reanimated';
import Slider from '@react-native-community/slider';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { IconSymbol } from '@/components/ui/icon-symbol';
import { useRobot } from '@/context/robot-provider';

export default function SettingsScreen() {
  const router = useRouter();
  const { baseUrl, setBaseUrl, refreshStatus, clearConnection, api } = useRobot();
  const [draftUrl, setDraftUrl] = useState(baseUrl);
  const [volume, setVolume] = useState(80);
  const [isLoadingVolume, setIsLoadingVolume] = useState(false);
  const [isMusicPlaying, setIsMusicPlaying] = useState(false);

  // Load current volume on mount
  useEffect(() => {
    const loadVolume = async () => {
      try {
        const response = await api.get('/control/volume');
        if (response.volume !== undefined) {
          setVolume(response.volume);
        }
      } catch (error) {
        console.warn('Failed to load volume', error);
      }
    };
    loadVolume();
  }, [api]);

  const handleSave = useCallback(() => {
    if (!draftUrl.startsWith('http')) {
      Alert.alert('Invalid URL', 'Please enter a full http:// or https:// address.');
      return;
    }

    setBaseUrl(draftUrl);
    refreshStatus();
  }, [draftUrl, refreshStatus, setBaseUrl]);

  const handleVolumeChange = useCallback(async (value: number) => {
    setVolume(value);
    setIsLoadingVolume(true);
    try {
      await api.post('/control/volume', { volume: Math.round(value) });
    } catch (error) {
      console.warn('Failed to set volume', error);
      Alert.alert('Volume Error', 'Failed to update speaker volume');
    } finally {
      setIsLoadingVolume(false);
    }
  }, [api]);

  const handlePlayMusic = useCallback(async () => {
    try {
      await api.post('/music/play', {});
      setIsMusicPlaying(true);
    } catch (error) {
      console.warn('Failed to play music', error);
      Alert.alert('Music Error', 'Failed to start music playback');
    }
  }, [api]);

  const handleStopMusic = useCallback(async () => {
    try {
      await api.post('/music/stop', {});
      setIsMusicPlaying(false);
    } catch (error) {
      console.warn('Failed to stop music', error);
      Alert.alert('Music Error', 'Failed to stop music');
    }
  }, [api]);

  const handleClearConnection = useCallback(() => {
    Alert.alert(
      'Clear Connection',
      'This will reset the robot connection. You will need to reconnect again.',
      [
        {
          text: 'Cancel',
          style: 'cancel',
        },
        {
          text: 'Clear',
          style: 'destructive',
          onPress: async () => {
            // Clear connection (status, baseUrl, and stored values)
            await clearConnection();
            // Navigate back to connection screen
            router.replace('/connection');
          },
        },
      ]
    );
  }, [clearConnection, router]);

  return (
    <SafeAreaView style={styles.safeArea} edges={['top']}>
      <ScrollView contentContainerStyle={styles.container} showsVerticalScrollIndicator={false}>
        <Animated.View entering={FadeInDown.duration(400)}>
          <ThemedText type="title">Settings</ThemedText>
          <ThemedText style={styles.description}>
            Configure robot connection and preferences
          </ThemedText>
        </Animated.View>

        <Animated.View entering={FadeInDown.delay(100).duration(400)}>
          <ThemedView style={styles.card}>
            <View style={styles.cardHeader}>
              <IconSymbol name="network" size={24} color="#3B82F6" />
              <ThemedText type="subtitle">Robot Connection</ThemedText>
            </View>
            <ThemedText style={styles.cardDescription}>
              Enter the robot's IP address or hostname
            </ThemedText>
            <TextInput
              value={draftUrl}
              onChangeText={setDraftUrl}
              style={styles.input}
              placeholder="http://192.168.1.100:8000"
              placeholderTextColor="#67686C"
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="url"
            />
            <Pressable 
              style={({ pressed }) => [
                styles.primaryButton,
                pressed && styles.primaryButtonPressed
              ]} 
              onPress={handleSave}
            >
              <IconSymbol name="checkmark.circle.fill" size={18} color="#04110B" />
              <ThemedText style={styles.primaryText}>Save Configuration</ThemedText>
            </Pressable>
          </ThemedView>
        </Animated.View>

        <Animated.View entering={FadeInDown.delay(200).duration(400)}>
          <ThemedView style={styles.card}>
            <View style={styles.cardHeader}>
              <IconSymbol name="speaker.wave.3.fill" size={24} color="#8B5CF6" />
              <ThemedText type="subtitle">Speaker Volume</ThemedText>
            </View>
            <ThemedText style={styles.cardDescription}>
              Adjust robot speaker loudness
            </ThemedText>
            <View style={styles.volumeContainer}>
              <IconSymbol name="speaker.wave.1.fill" size={20} color="#67686C" />
              <Slider
                style={styles.slider}
                minimumValue={0}
                maximumValue={100}
                value={volume}
                onValueChange={setVolume}
                onSlidingComplete={handleVolumeChange}
                minimumTrackTintColor="#8B5CF6"
                maximumTrackTintColor="rgba(55, 55, 55, 0.6)"
                thumbTintColor="#8B5CF6"
                disabled={isLoadingVolume}
              />
              <IconSymbol name="speaker.wave.3.fill" size={20} color="#8B5CF6" />
            </View>
            <View style={styles.volumeValue}>
              <ThemedText style={styles.volumeText}>{Math.round(volume)}%</ThemedText>
            </View>
          </ThemedView>
        </Animated.View>

        <Animated.View entering={FadeInDown.delay(300).duration(400)}>
          <ThemedView style={styles.card}>
            <View style={styles.cardHeader}>
              <IconSymbol name="music.note" size={24} color="#EC4899" />
              <ThemedText type="subtitle">Music Player</ThemedText>
            </View>
            <ThemedText style={styles.cardDescription}>
              Play music from YouTube on robot speakers
            </ThemedText>
            <View style={styles.musicControls}>
              <Pressable 
                style={({ pressed }) => [
                  styles.musicButton,
                  !isMusicPlaying && styles.musicButtonPrimary,
                  pressed && styles.musicButtonPressed
                ]} 
                onPress={handlePlayMusic}
                disabled={isMusicPlaying}
              >
                <IconSymbol name="play.fill" size={20} color={isMusicPlaying ? "#67686C" : "#FFFFFF"} />
                <ThemedText style={[styles.musicButtonText, !isMusicPlaying && styles.musicButtonTextPrimary]}>
                  Play Music
                </ThemedText>
              </Pressable>
              <Pressable 
                style={({ pressed }) => [
                  styles.musicButton,
                  isMusicPlaying && styles.musicButtonDanger,
                  pressed && styles.musicButtonPressed
                ]} 
                onPress={handleStopMusic}
                disabled={!isMusicPlaying}
              >
                <IconSymbol name="stop.fill" size={20} color={isMusicPlaying ? "#FFFFFF" : "#67686C"} />
                <ThemedText style={[styles.musicButtonText, isMusicPlaying && styles.musicButtonTextDanger]}>
                  Stop
                </ThemedText>
              </Pressable>
            </View>
            {isMusicPlaying && (
              <View style={styles.musicStatus}>
                <IconSymbol name="waveform" size={16} color="#EC4899" />
                <ThemedText style={styles.musicStatusText}>Music playing...</ThemedText>
              </View>
            )}
          </ThemedView>
        </Animated.View>

        <Animated.View entering={FadeInDown.delay(400).duration(400)}>
          <ThemedView style={styles.card}>
            <View style={styles.cardHeader}>
              <IconSymbol name="arrow.triangle.2.circlepath" size={24} color="#F59E0B" />
              <ThemedText type="subtitle">Reset Connection</ThemedText>
            </View>
            <ThemedText style={styles.cardDescription}>
              Clear the current connection and return to discovery screen
            </ThemedText>
            <Pressable 
              style={({ pressed }) => [
                styles.dangerButton,
                pressed && styles.dangerButtonPressed
              ]} 
              onPress={handleClearConnection}
            >
              <IconSymbol name="trash.fill" size={18} color="#FFFFFF" />
              <ThemedText style={styles.dangerText}>Clear Connection</ThemedText>
            </Pressable>
          </ThemedView>
        </Animated.View>

        <Animated.View entering={FadeInDown.delay(500).duration(400)}>
          <ThemedView style={styles.card}>
            <View style={styles.cardHeader}>
              <IconSymbol name="info.circle.fill" size={24} color="#6366F1" />
              <ThemedText type="subtitle">About</ThemedText>
            </View>
            <View style={styles.infoRow}>
              <ThemedText style={styles.infoLabel}>App Name</ThemedText>
              <ThemedText style={styles.infoValue}>JARVIS Controller</ThemedText>
            </View>
            <View style={styles.infoRow}>
              <ThemedText style={styles.infoLabel}>Version</ThemedText>
              <ThemedText style={styles.infoValue}>1.0.0</ThemedText>
            </View>
            <View style={styles.infoRow}>
              <ThemedText style={styles.infoLabel}>Platform</ThemedText>
              <ThemedText style={styles.infoValue}>Raspberry Pi 5</ThemedText>
            </View>
            <ThemedText style={styles.meta}>
              Robot companion dashboard with Wi-Fi setup, camera streaming, voice control, and telemetry monitoring.
            </ThemedText>
          </ThemedView>
        </Animated.View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#0F0F0F',
  },
  container: {
    padding: 20,
    gap: 20,
    backgroundColor: '#0F0F0F',
    paddingBottom: 40,
  },
  description: {
    color: '#9CA3AF',
    marginTop: 6,
    fontSize: 14,
  },
  card: {
    gap: 16,
    padding: 20,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: 'rgba(37, 37, 37, 0.6)',
    backgroundColor: 'rgba(26, 26, 26, 0.7)',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 2,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  cardDescription: {
    color: '#9CA3AF',
    fontSize: 14,
    lineHeight: 20,
  },
  input: {
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: 'rgba(55, 55, 55, 0.6)',
    backgroundColor: 'rgba(15, 15, 15, 0.8)',
    color: '#F9FAFB',
    fontFamily: 'JetBrainsMono_400Regular',
    fontSize: 14,
  },
  primaryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#1DD1A1',
    borderRadius: 12,
    paddingVertical: 16,
    shadowColor: '#1DD1A1',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  primaryButtonPressed: {
    backgroundColor: '#17B891',
    transform: [{ scale: 0.98 }],
  },
  primaryText: {
    color: '#04110B',
    fontFamily: 'JetBrainsMono_600SemiBold',
    fontSize: 15,
  },
  dangerButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#EF4444',
    borderRadius: 12,
    paddingVertical: 16,
    shadowColor: '#EF4444',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 4,
  },
  dangerButtonPressed: {
    backgroundColor: '#DC2626',
    transform: [{ scale: 0.98 }],
  },
  dangerText: {
    color: '#FFFFFF',
    fontFamily: 'JetBrainsMono_600SemiBold',
    fontSize: 15,
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
  meta: {
    color: '#67686C',
    fontSize: 13,
    lineHeight: 18,
    marginTop: 8,
  },
  volumeContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 8,
  },
  slider: {
    flex: 1,
    height: 40,
  },
  volumeValue: {
    alignItems: 'center',
    paddingVertical: 4,
  },
  volumeText: {
    fontSize: 24,
    fontFamily: 'JetBrainsMono_600SemiBold',
    color: '#8B5CF6',
  },
  musicControls: {
    flexDirection: 'row',
    gap: 12,
  },
  musicButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: 'rgba(55, 55, 55, 0.6)',
    borderRadius: 12,
    paddingVertical: 14,
    borderWidth: 1,
    borderColor: 'rgba(55, 55, 55, 0.6)',
  },
  musicButtonPrimary: {
    backgroundColor: '#EC4899',
    borderColor: '#EC4899',
  },
  musicButtonDanger: {
    backgroundColor: '#EF4444',
    borderColor: '#EF4444',
  },
  musicButtonPressed: {
    transform: [{ scale: 0.96 }],
    opacity: 0.8,
  },
  musicButtonText: {
    color: '#67686C',
    fontFamily: 'JetBrainsMono_600SemiBold',
    fontSize: 14,
  },
  musicButtonTextPrimary: {
    color: '#FFFFFF',
  },
  musicButtonTextDanger: {
    color: '#FFFFFF',
  },
  musicStatus: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    justifyContent: 'center',
    paddingVertical: 8,
  },
  musicStatusText: {
    color: '#EC4899',
    fontSize: 13,
    fontFamily: 'JetBrainsMono_600SemiBold',
  },
});
