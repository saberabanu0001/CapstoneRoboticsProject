import { Platform } from "react-native";

export type BleState =
  | "Unknown"
  | "Resetting"
  | "Unsupported"
  | "Unauthorized"
  | "PoweredOff"
  | "PoweredOn";

export interface OptionalBleManager {
  startDeviceScan: (
    uuids: string[] | null,
    options: unknown,
    listener: (
      error: Error | null,
      device: { id: string; name: string | null; rssi: number | null } | null
    ) => void
  ) => void;
  stopDeviceScan: () => void;
  destroy: () => void;
  onStateChange?: (
    listener: (state: BleState) => void,
    emitCurrentState?: boolean
  ) => { remove: () => void } | undefined;
  state?: () => Promise<BleState>;
  enable?: () => Promise<void>;
}

/**
 * Attempts to load react-native-ble-plx module.
 * Returns null if the module is not available or not installed.
 * This allows Metro bundler to handle the optional dependency gracefully.
 */
export function loadBleManager(): OptionalBleManager | null {
  // Skip on web platform
  if (Platform.OS === "web") {
    return null;
  }

  try {
    // Static require - Metro bundler needs to see the exact string literal
    // If the module isn't installed, Metro will fail at build time
    // To use BLE, install: npm install react-native-ble-plx
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const bleModule = require("react-native-ble-plx") as
      | { BleManager: new () => OptionalBleManager }
      | undefined;

    if (!bleModule?.BleManager) {
      return null;
    }

    return new bleModule.BleManager();
  } catch (error) {
    // Module not installed or not available
    console.log("react-native-ble-plx not available:", error);
    return null;
  }
}

