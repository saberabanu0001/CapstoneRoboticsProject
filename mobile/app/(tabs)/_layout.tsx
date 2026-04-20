import { Redirect, Tabs } from 'expo-router';
import React from 'react';

import { HapticTab } from '@/components/haptic-tab';
import { IconSymbol } from '@/components/ui/icon-symbol';
import { Colors } from '@/constants/theme';
import { useRobot } from '@/context/robot-provider';
import { useColorScheme } from '@/hooks/use-color-scheme';

export default function TabLayout() {
  const colorScheme = useColorScheme();
  const { status } = useRobot();

  const isConnected = Boolean(status?.network?.ip);

  if (!isConnected) {
    return <Redirect href="/connection" />;
  }

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: Colors[colorScheme ?? 'light'].tint,
        headerShown: false,
        tabBarButton: HapticTab,
      }}>
      <Tabs.Screen
        name="home"
        options={{
          title: 'Home',
          tabBarIcon: ({ color }) => <IconSymbol size={26} name="house.fill" color={color} />,
        }}
      />
      <Tabs.Screen
        name="status"
        options={{
          title: 'Summaries',
          tabBarIcon: ({ color }) => <IconSymbol size={26} name="book" color={color} />,
        }}
      />
      <Tabs.Screen
        name="photo-time"
        options={{
          title: 'Photo Time',
          tabBarIcon: ({ color }) => <IconSymbol size={26} name="camera.fill" color={color} />,
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{
          title: 'Settings',
          tabBarIcon: ({ color }) => <IconSymbol size={26} name="gearshape" color={color} />,
        }}
      />
    </Tabs>
  );
}
