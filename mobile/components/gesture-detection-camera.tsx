import React, { useRef, useEffect, useCallback } from 'react';
import { View, StyleSheet, Platform } from 'react-native';
import { CameraView, useCameraPermissions, CameraType } from 'expo-camera';
import { useGestureDetection } from '@/hooks/useGestureDetection';

interface GestureDetectionCameraProps {
  enabled?: boolean;
  baseUrl?: string;
  onGestureDetected?: (gesture: 'like' | 'heart' | 'none') => void;
  detectionInterval?: number;
}

/**
 * Hidden camera component that captures frames from front camera
 * and detects hand gestures in the background
 */
export function GestureDetectionCamera({
  enabled = true,
  baseUrl,
  onGestureDetected,
  detectionInterval = 500,
}: GestureDetectionCameraProps) {
  const cameraRef = useRef<CameraView>(null);
  const [permission, requestPermission] = useCameraPermissions();
  const [hasPermission, setHasPermission] = React.useState<boolean | null>(null);
  const captureIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastCaptureTimeRef = useRef(0);

  const { detectGestureFromImage } = useGestureDetection({
    enabled: enabled && hasPermission === true,
    baseUrl,
    onGestureDetected,
    detectionInterval,
  });

  // Request camera permission
  useEffect(() => {
    if (!permission) {
      requestPermission();
    } else {
      setHasPermission(permission.granted);
      if (!permission.granted && permission.canAskAgain) {
        requestPermission();
      }
    }
  }, [permission, requestPermission]);

  const captureFrame = useCallback(async () => {
    if (!enabled || !hasPermission || !cameraRef.current) {
      return;
    }

    // Throttle captures
    const now = Date.now();
    if (now - lastCaptureTimeRef.current < detectionInterval) {
      return;
    }
    lastCaptureTimeRef.current = now;

    try {
      // Take picture (low quality for speed)
      const photo = await cameraRef.current.takePictureAsync({
        quality: 0.3, // Low quality for faster processing
        base64: true,
        skipProcessing: false,
      });

      if (photo?.base64) {
        // Convert to data URI
        const imageDataUri = `data:image/jpeg;base64,${photo.base64}`;
        
        // Detect gesture
        detectGestureFromImage(imageDataUri);
      }
    } catch (error) {
      // Silently fail - camera might be busy
      console.debug('Failed to capture frame for gesture detection:', error);
    }
  }, [enabled, hasPermission, detectionInterval, detectGestureFromImage]);

  // Start/stop frame capture
  useEffect(() => {
    if (enabled && hasPermission) {
      // Start capturing frames periodically
      captureIntervalRef.current = setInterval(() => {
        captureFrame();
      }, detectionInterval);
    } else {
      if (captureIntervalRef.current) {
        clearInterval(captureIntervalRef.current);
        captureIntervalRef.current = null;
      }
    }

    return () => {
      if (captureIntervalRef.current) {
        clearInterval(captureIntervalRef.current);
        captureIntervalRef.current = null;
      }
    };
  }, [enabled, hasPermission, captureFrame, detectionInterval]);

  // Don't render if no permission or not enabled
  if (!enabled || hasPermission === false) {
    return null;
  }

  return (
    <View style={styles.hiddenCamera}>
      <CameraView
        ref={cameraRef}
        style={styles.camera}
        facing="front"
        mode="picture"
        autofocus="on"
      />
    </View>
  );
}

const styles = StyleSheet.create({
  hiddenCamera: {
    position: 'absolute',
    width: 1,
    height: 1,
    opacity: 0,
    overflow: 'hidden',
    zIndex: -1,
    ...(Platform.OS === 'ios' && {
      left: -1000,
      top: -1000,
    }),
  },
  camera: {
    width: 1,
    height: 1,
  },
});

