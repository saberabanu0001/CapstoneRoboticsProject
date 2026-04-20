import { DarkTheme, ThemeProvider } from '@react-navigation/native';
import { useFonts } from 'expo-font';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';
import 'react-native-reanimated';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { GestureHandlerRootView } from 'react-native-gesture-handler';

import {
  JetBrainsMono_400Regular,
  JetBrainsMono_600SemiBold,
} from '@expo-google-fonts/jetbrains-mono';
import {
  Lato_100Thin,
  Lato_100Thin_Italic,
  Lato_300Light,
  Lato_300Light_Italic,
  Lato_400Regular,
  Lato_400Regular_Italic,
  Lato_700Bold,
  Lato_700Bold_Italic,
  Lato_900Black,
  Lato_900Black_Italic,
} from '@expo-google-fonts/lato';
import {
  Lora_400Regular,
  Lora_500Medium,
  Lora_600SemiBold,
  Lora_700Bold,
} from '@expo-google-fonts/lora';

import { RobotProvider } from '@/context/robot-provider';

export const unstable_settings = {
  anchor: '(tabs)',
};

export default function RootLayout() {
  let [fontsLoaded, fontError] = useFonts({
    Lato_100Thin,
    Lato_100Thin_Italic,
    Lato_300Light,
    Lato_300Light_Italic,
    Lato_400Regular,
    Lato_400Regular_Italic,
    Lato_700Bold,
    Lato_700Bold_Italic,
    Lato_900Black,
    Lato_900Black_Italic,
    JetBrainsMono_400Regular,
    JetBrainsMono_600SemiBold,
    Lora_400Regular,
    Lora_500Medium,
    Lora_600SemiBold,
    Lora_700Bold,
  });

  useEffect(() => {
    if (fontError) {
      console.error('Failed to load fonts', fontError);
    }
  }, [fontError]);

  if (!fontsLoaded && !fontError) {
    return null;
  }

  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <SafeAreaProvider>
        <RobotProvider>
          <ThemeProvider value={DarkTheme}>
            <Stack>
              <Stack.Screen name="connection" options={{ headerShown: false }} />
              <Stack.Screen name="manual" options={{ headerShown: false }} />
              <Stack.Screen name="agentic" options={{ headerShown: false }} />
              <Stack.Screen name="wifi" options={{ headerShown: false }} />
              <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
              <Stack.Screen name="modal" options={{ presentation: 'modal', title: 'Modal' }} />
            </Stack>
            <StatusBar style="light" />
          </ThemeProvider>
        </RobotProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}
