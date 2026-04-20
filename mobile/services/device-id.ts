import * as SecureStore from "expo-secure-store";
import { randomUUID } from "expo-crypto";

const DEVICE_ID_STORAGE_KEY = "device_id";

/**
 * Gets or generates a stable device ID for this app installation.
 * The device ID persists across app restarts but is unique per installation.
 */
export async function getDeviceId(): Promise<string> {
  try {
    // Check if SecureStore is available
    if (SecureStore.isAvailableAsync && !(await SecureStore.isAvailableAsync())) {
      console.warn("SecureStore is not available, generating temporary device ID");
      // Fallback to a temporary in-memory ID (won't persist)
      return `temp-${randomUUID()}`;
    }

    // Try to get existing device ID
    const existingId = await SecureStore.getItemAsync(DEVICE_ID_STORAGE_KEY);
    if (existingId) {
      return existingId;
    }

    // Generate new device ID
    const newId = randomUUID();
    await SecureStore.setItemAsync(DEVICE_ID_STORAGE_KEY, newId);
    console.log("Generated new device ID:", newId);
    return newId;
  } catch (error) {
    console.error("Failed to get or generate device ID", error);
    // Fallback to a temporary ID
    return `temp-${randomUUID()}`;
  }
}

/**
 * Gets device information for pairing requests.
 */
export async function getDeviceInfo(): Promise<{
  device_id: string;
  name?: string;
  platform: string;
  app_version?: string;
}> {
  const deviceId = await getDeviceId();
  const platform = "mobile"; // Could be enhanced to detect iOS/Android/Web

  // Try to get device name (optional)
  let deviceName: string | undefined;
  try {
    // On native platforms, you might want to use expo-device or similar
    // For now, we'll use a generic name
    deviceName = undefined;
  } catch (error) {
    // Ignore errors getting device name
  }

  return {
    device_id: deviceId,
    name: deviceName,
    platform,
  };
}

