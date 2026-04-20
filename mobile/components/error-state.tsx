import React from 'react';
import { StyleSheet, View, Pressable } from 'react-native';
import Animated, { FadeIn } from 'react-native-reanimated';

import { ThemedText } from './themed-text';
import { IconSymbol } from './ui/icon-symbol';

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  retryLabel?: string;
}

export function ErrorState({ 
  title = 'Something went wrong',
  message, 
  onRetry,
  retryLabel = 'Try again'
}: ErrorStateProps) {
  return (
    <Animated.View entering={FadeIn.duration(400)} style={styles.container}>
      <View style={styles.iconContainer}>
        <IconSymbol name="exclamationmark.triangle.fill" size={48} color="#EF4444" />
      </View>
      <ThemedText style={styles.title}>{title}</ThemedText>
      <ThemedText style={styles.message}>{message}</ThemedText>
      {onRetry && (
        <Pressable 
          style={({ pressed }) => [
            styles.retryButton,
            pressed && styles.retryButtonPressed
          ]}
          onPress={onRetry}
        >
          <IconSymbol name="arrow.clockwise" size={16} color="#E5E7EB" />
          <ThemedText style={styles.retryText}>{retryLabel}</ThemedText>
        </Pressable>
      )}
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
    padding: 32,
    gap: 12,
  },
  iconContainer: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 8,
  },
  title: {
    fontSize: 18,
    fontFamily: 'JetBrainsMono_600SemiBold',
    color: '#E5E7EB',
    textAlign: 'center',
  },
  message: {
    fontSize: 14,
    color: '#9CA3AF',
    textAlign: 'center',
    lineHeight: 20,
  },
  retryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 20,
    paddingVertical: 12,
    backgroundColor: 'rgba(26, 26, 26, 0.7)',
    borderWidth: 1,
    borderColor: 'rgba(37, 37, 37, 0.6)',
    borderRadius: 12,
    marginTop: 8,
  },
  retryButtonPressed: {
    backgroundColor: 'rgba(34, 34, 34, 0.9)',
    transform: [{ scale: 0.97 }],
  },
  retryText: {
    fontSize: 14,
    fontFamily: 'JetBrainsMono_600SemiBold',
    color: '#E5E7EB',
  },
});

