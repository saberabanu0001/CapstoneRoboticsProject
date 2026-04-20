import * as FileSystem from 'expo-file-system/legacy';
import { Platform } from 'react-native';
import { DEFAULT_CLOUD_URL } from './cloud-api';

export type DetectedGesture = 'like' | 'heart' | 'none';

interface GestureDetectionResponse {
  gesture: DetectedGesture;
  confidence: number;
  status: string;
}

/**
 * Service for detecting hand gestures from images
 * Uses the cloud server's MediaPipe-based gesture detection
 */
export class GestureDetectionService {
  private baseUrl: string;
  private detectionInterval: number = 500; // ms between detections
  private lastDetectionTime: number = 0;

  constructor(baseUrl: string = DEFAULT_CLOUD_URL) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
  }

  /**
   * Detect gesture from image data URI or base64 string
   */
  async detectGesture(imageDataUri: string): Promise<DetectedGesture> {
    try {
      // Throttle requests to avoid overwhelming the server
      const now = Date.now();
      if (now - this.lastDetectionTime < this.detectionInterval) {
        return 'none';
      }
      this.lastDetectionTime = now;

      // Extract base64 data from data URI
      const base64Data = imageDataUri.split(',')[1] || imageDataUri;

      // For React Native, we need to save the base64 image to a temporary file
      // because FormData doesn't support Blob or data URIs directly
      const fileName = `gesture_${Date.now()}.jpg`;
      const fileUri = `${FileSystem.cacheDirectory}${fileName}`;
      
      // Write base64 data to file
      await FileSystem.writeAsStringAsync(fileUri, base64Data, {
        encoding: FileSystem.EncodingType.Base64,
      });

      // Verify file was written
      const fileInfo = await FileSystem.getInfoAsync(fileUri);
      if (!fileInfo.exists) {
        console.warn('Failed to write gesture detection file');
        return 'none';
      }

      // Platform-specific file URI handling
      // iOS needs file:// prefix for FormData
      const finalUri = Platform.OS === 'ios' 
        ? (fileUri.startsWith('file://') ? fileUri : `file://${fileUri}`)
        : fileUri;

      // Create FormData with file URI (React Native format)
      // React Native FormData requires: { uri, type, name }
      const formData = new FormData();
      formData.append('file', {
        uri: finalUri,
        type: 'image/jpeg',
        name: fileName,
      } as any);

      // Send to server
      // Note: Don't set Content-Type header - React Native sets it automatically with boundary
      const requestUrl = `${this.baseUrl}/gesture/detect`;
      console.log('Sending gesture detection request to:', requestUrl);
      
      const response = await fetch(requestUrl, {
        method: 'POST',
        body: formData,
      });

      // Clean up temporary file (even if request fails)
      try {
        await FileSystem.deleteAsync(fileUri, { idempotent: true });
      } catch (cleanupError) {
        console.warn('Failed to delete temporary gesture file', cleanupError);
      }

      if (!response.ok) {
        const errorText = await response.text().catch(() => 'Unknown error');
        console.warn('Gesture detection failed:', {
          status: response.status,
          statusText: response.statusText,
          error: errorText,
        });
        return 'none';
      }

      const result: GestureDetectionResponse = await response.json();
      
      // Only return gesture if confidence is above threshold
      if (result.confidence > 0.5) {
        return result.gesture;
      }

      return 'none';
    } catch (error) {
      console.error('Gesture detection error:', {
        error,
        baseUrl: this.baseUrl,
        message: error instanceof Error ? error.message : String(error),
      });
      return 'none';
    }
  }

  /**
   * Update base URL for gesture detection service
   */
  updateBaseUrl(baseUrl: string) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
  }
}

// Singleton instance
let gestureDetectionService: GestureDetectionService | null = null;

export function getGestureDetectionService(baseUrl?: string): GestureDetectionService {
  if (!gestureDetectionService) {
    gestureDetectionService = new GestureDetectionService(baseUrl);
  } else if (baseUrl) {
    gestureDetectionService.updateBaseUrl(baseUrl);
  }
  return gestureDetectionService;
}
