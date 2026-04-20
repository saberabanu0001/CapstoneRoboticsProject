import React from 'react';
import { StyleSheet, View } from 'react-native';
import Animated, { FadeIn } from 'react-native-reanimated';
import { Image } from 'expo-image';

import { ThemedText } from './themed-text';
import { IconSymbol } from './ui/icon-symbol';

interface EmptyStateProps {
  icon?: string;
  image?: any;
  title: string;
  message: string;
}

export function EmptyState({ icon, image, title, message }: EmptyStateProps) {
  return (
    <Animated.View entering={FadeIn.duration(400)} style={styles.container}>
      {image ? (
        <Image
          source={image}
          style={styles.image}
          contentFit="contain"
        />
      ) : icon ? (
        <View style={styles.iconContainer}>
          <IconSymbol name={icon} size={48} color="#67686C" />
        </View>
      ) : null}
      <ThemedText style={styles.title}>{title}</ThemedText>
      <ThemedText style={styles.message}>{message}</ThemedText>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
    padding: 48,
    gap: 12,
  },
  iconContainer: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: 'rgba(55, 55, 55, 0.2)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 8,
  },
  image: {
    width: 120,
    height: 80,
    marginBottom: 12,
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
    paddingHorizontal: 20,
  },
});

