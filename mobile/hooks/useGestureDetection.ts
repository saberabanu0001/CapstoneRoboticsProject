import { useEffect, useRef, useState, useCallback } from 'react';
import { getGestureDetectionService, DetectedGesture } from '@/services/gesture-detection';

interface UseGestureDetectionOptions {
  enabled?: boolean;
  baseUrl?: string;
  onGestureDetected?: (gesture: DetectedGesture) => void;
  detectionInterval?: number; // ms between detections
}

/**
 * Hook for detecting hand gestures using camera frames
 * Uses server-side MediaPipe Hands for gesture detection
 */
export function useGestureDetection(options: UseGestureDetectionOptions = {}) {
  const { 
    enabled = true, 
    baseUrl,
    onGestureDetected,
    detectionInterval = 500 
  } = options;
  
  const [gesture, setGesture] = useState<DetectedGesture>('none');
  const [isDetecting, setIsDetecting] = useState(false);
  const detectionServiceRef = useRef(getGestureDetectionService(baseUrl));
  const lastDetectionTimeRef = useRef(0);
  const detectionTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Update service base URL if provided
  useEffect(() => {
    if (baseUrl) {
      detectionServiceRef.current.updateBaseUrl(baseUrl);
    }
  }, [baseUrl]);

  const detectGestureFromImage = useCallback(async (imageDataUri: string) => {
    if (!enabled || isDetecting) {
      return;
    }

    // Throttle to avoid overwhelming the server
    const now = Date.now();
    if (now - lastDetectionTimeRef.current < detectionInterval) {
      return;
    }
    lastDetectionTimeRef.current = now;

    setIsDetecting(true);
    try {
      const detectedGesture = await detectionServiceRef.current.detectGesture(imageDataUri);
      
      if (detectedGesture !== gesture) {
        setGesture(detectedGesture);
        onGestureDetected?.(detectedGesture);
      }
    } catch (error) {
      console.error('Gesture detection error:', error);
    } finally {
      setIsDetecting(false);
    }
  }, [enabled, isDetecting, gesture, onGestureDetected, detectionInterval]);

  // Clear timeout on unmount
  useEffect(() => {
    return () => {
      if (detectionTimeoutRef.current) {
        clearTimeout(detectionTimeoutRef.current);
      }
    };
  }, []);

  const updateGesture = useCallback((newGesture: DetectedGesture) => {
    if (newGesture !== gesture) {
      setGesture(newGesture);
      onGestureDetected?.(newGesture);
    }
  }, [gesture, onGestureDetected]);

  return {
    gesture,
    isDetecting,
    detectGestureFromImage,
    updateGesture,
    isReady: enabled,
  };
}

