import { PermissionsAndroid, Platform } from "react-native";
import type {
  BleError,
  Characteristic,
  Device,
  Service,
} from "react-native-ble-plx";
import { BleManager } from "react-native-ble-plx";

// Wi-Fi service UUID
const WIFI_SERVICE_UUID = "1234abcd-0000-1000-8000-00805f9b34fb";

// Characteristic UUIDs
const WIFI_CONFIG_CHARACTERISTIC_UUID = "1234abcd-0001-1000-8000-00805f9b34fb";
const WIFI_STATUS_CHARACTERISTIC_UUID = "1234abcd-0002-1000-8000-00805f9b34fb";

// Device name prefix for filtering

// Wi-Fi status values
export type WifiStatus = "idle" | "connecting" | "connected" | "failed";

// Device info returned from scan
export interface RovyDevice {
  id: string;
  name: string;
  rssi?: number | null;
}

// Callback type for status changes
export type StatusChangeCallback = (status: WifiStatus) => void;

// Callback type for device discovery during scanning
export type DeviceFoundCallback = (device: RovyDevice) => void;

/**
 * ROVY BLE Manager for Wi-Fi configuration
 * Handles scanning, connecting, and configuring Wi-Fi via BLE
 */
export class RovyBleManager {
  private bleManager: BleManager | null = null;
  private connectedDevice: Device | null = null;
  private wifiConfigCharacteristic: Characteristic | null = null;
  private wifiStatusCharacteristic: Characteristic | null = null;
  private statusChangeCallbacks: Set<StatusChangeCallback> = new Set();
  private statusSubscription: { remove: () => void } | null = null;
  private currentStatus: WifiStatus = "idle";
  private bleUnavailableReason: string | null = null;

  constructor() {
    try {
      // Skip on web platform
      if (Platform.OS === "web") {
        this.bleUnavailableReason =
          "Bluetooth provisioning is not supported in the web preview. Please run the mobile app on iOS or Android.";
        console.warn(this.bleUnavailableReason);
        this.bleManager = null;
        return;
      }

      // Create BleManager directly - react-native-ble-plx handles native module linking
      // If the native module isn't available, this will throw an error which we catch below
      this.bleManager = new BleManager();
      this.bleUnavailableReason = null;
      console.log("BLE manager initialized successfully");
    } catch (error) {
      console.error("Error initializing BLE manager:", error);
      const message =
        error instanceof Error
          ? error.message
          : "Unknown Bluetooth initialization error";

      // Check if this is a native module not found or not linked error
      if (
        message.includes("Native module") ||
        message.includes("not found") ||
        message.includes("Cannot find module") ||
        message.includes("NativeEventEmitter") ||
        message.includes("requires a non-null argument")
      ) {
        this.bleUnavailableReason =
          "Bluetooth provisioning requires a native build with BLE support. Rebuild the app with `expo run:ios` or `expo run:android`.";
      } else {
        this.bleUnavailableReason =
          "Failed to initialize Bluetooth manager: " + message;
      }
      this.bleManager = null;
    }
  }

  private getAvailabilityError(): Error {
    const reason =
      this.bleUnavailableReason ||
      "Bluetooth manager not available. Restart the app to re-initialize BLE.";
    return new Error(reason);
  }

  /**
   * Check and request BLE permissions
   * Note: iOS permissions are handled via Info.plist
   * Android requires runtime permissions for BLE scanning
   */
  private async checkPermissions(): Promise<boolean> {
    if (Platform.OS === "android") {
      // Android 12+ requires BLUETOOTH_SCAN permission
      const apiLevel = Platform.Version;
      if (apiLevel >= 31) {
        try {
          const scanPermission = PermissionsAndroid.PERMISSIONS.BLUETOOTH_SCAN;
          const connectPermission =
            PermissionsAndroid.PERMISSIONS.BLUETOOTH_CONNECT;

          const hasScanPermission = await PermissionsAndroid.check(
            scanPermission
          );
          const hasConnectPermission = await PermissionsAndroid.check(
            connectPermission
          );

          if (!hasScanPermission || !hasConnectPermission) {
            const granted = await PermissionsAndroid.requestMultiple([
              scanPermission,
              connectPermission,
            ]);

            const scanGranted =
              granted[scanPermission] === PermissionsAndroid.RESULTS.GRANTED;
            const connectGranted =
              granted[connectPermission] === PermissionsAndroid.RESULTS.GRANTED;

            if (!scanGranted || !connectGranted) {
              console.warn("BLE permissions not granted");
              return false;
            }
          }
        } catch (error) {
          console.error("Error requesting BLE permissions:", error);
          return false;
        }
      } else {
        // Android < 12 uses location permission for BLE scanning
        try {
          const locationPermission =
            PermissionsAndroid.PERMISSIONS.ACCESS_FINE_LOCATION;
          const hasPermission = await PermissionsAndroid.check(
            locationPermission
          );

          if (!hasPermission) {
            const granted = await PermissionsAndroid.request(
              locationPermission,
              {
                title: "Location Permission",
                message:
                  "This app needs location permission to scan for Bluetooth devices.",
                buttonNeutral: "Ask Me Later",
                buttonNegative: "Cancel",
                buttonPositive: "OK",
              }
            );

            if (granted !== PermissionsAndroid.RESULTS.GRANTED) {
              console.warn("Location permission not granted for BLE scanning");
              return false;
            }
          }
        } catch (error) {
          console.error("Error requesting location permission:", error);
          return false;
        }
      }
    }

    // iOS permissions are handled via Info.plist (NSBluetoothAlwaysUsageDescription)
    return true;
  }

  /**
   * Check if BLE is available and powered on
   */
  private async ensureBleReady(): Promise<void> {
    if (!this.bleManager) {
      throw this.getAvailabilityError();
    }

    // Check BLE state
    const state = await this.bleManager.state();
    console.log("BLE state:", state);

    if (state === "PoweredOff") {
      throw new Error("Bluetooth is turned off. Please enable Bluetooth.");
    }

    if (state === "Unsupported") {
      throw new Error("Bluetooth Low Energy is not supported on this device.");
    }

    if (state === "Unauthorized") {
      throw new Error(
        "Bluetooth permission denied. Please grant Bluetooth permissions in settings."
      );
    }

    if (state !== "PoweredOn") {
      throw new Error(`Bluetooth is not ready. Current state: ${state}`);
    }
  }

  /**
   * Scan for nearby ROVY devices
   * Filters devices whose name starts with "ROVY-"
   * @param onDeviceFound Optional callback that gets called when a device is found during scanning
   * @returns Promise that resolves with all found devices after scan completes
   */
  async scanForRovy(
    onDeviceFound?: DeviceFoundCallback
  ): Promise<RovyDevice[]> {
    console.log("Starting scan for devices...");

    if (!this.bleManager) {
      throw this.getAvailabilityError();
    }

    // Check permissions
    const hasPermission = await this.checkPermissions();
    if (!hasPermission) {
      throw new Error("Bluetooth permissions not granted");
    }

    // Ensure BLE is ready
    await this.ensureBleReady();

    return new Promise((resolve, reject) => {
      if (!this.bleManager) {
        reject(this.getAvailabilityError());
        return;
      }

      const foundDevices = new Map<string, RovyDevice>();
      const scanTimeout = setTimeout(() => {
        this.bleManager?.stopDeviceScan();
        console.log(`Scan completed. Found ${foundDevices.size} device(s).`);
        resolve(Array.from(foundDevices.values()));
      }, 10000); // 10 second scan timeout

      this.bleManager.startDeviceScan(
        null, // Scan for all devices
        { allowDuplicates: false },
        (error: Error | null, device: Device | null) => {
          if (error) {
            clearTimeout(scanTimeout);
            this.bleManager?.stopDeviceScan();
            console.error("BLE scan error:", error);
            reject(error as BleError);
            return;
          }

          if (device?.name) {
            console.log("Found device:", device.name, device.id, device.rssi);
            const rovyDevice: RovyDevice = {
              id: device.id,
              name: device.name,
              rssi: device.rssi ?? null,
            };
            foundDevices.set(device.id, rovyDevice);

            // Call the callback immediately when a device is found
            if (onDeviceFound) {
              try {
                onDeviceFound(rovyDevice);
              } catch (error) {
                console.error("Error in onDeviceFound callback:", error);
              }
            }
          }
        }
      );
    });
  }

  /**
   * Connect to a ROVY device by its ID
   * Discovers services and characteristics, subscribes to wifi_status notifications
   */
  async connectToRovy(deviceId: string): Promise<void> {
    console.log("Connecting to device:", deviceId);

    if (!this.bleManager) {
      throw this.getAvailabilityError();
    }

    // Ensure BLE is ready
    await this.ensureBleReady();

    try {
      // Connect to device
      const device = await this.bleManager.connectToDevice(deviceId);
      console.log("Connected to device:", device.id);

      // Discover services and characteristics
      const deviceWithServices =
        await device.discoverAllServicesAndCharacteristics();
      console.log("Services and characteristics discovered");

      // Find the Wi-Fi service
      const services = await deviceWithServices.services();
      const wifiService = services.find(
        (service: Service) =>
          service.uuid.toLowerCase() === WIFI_SERVICE_UUID.toLowerCase()
      );

      if (!wifiService) {
        throw new Error(
          `Wi-Fi service not found. Expected UUID: ${WIFI_SERVICE_UUID}`
        );
      }

      console.log("Found Wi-Fi service:", wifiService.uuid);

      // Find characteristics
      const characteristics = await wifiService.characteristics();
      console.log(
        `Found ${characteristics.length} characteristic(s) in Wi-Fi service`
      );

      const wifiConfigChar = characteristics.find(
        (char: Characteristic) =>
          char.uuid.toLowerCase() ===
          WIFI_CONFIG_CHARACTERISTIC_UUID.toLowerCase()
      );

      const wifiStatusChar = characteristics.find(
        (char: Characteristic) =>
          char.uuid.toLowerCase() ===
          WIFI_STATUS_CHARACTERISTIC_UUID.toLowerCase()
      );

      if (!wifiConfigChar) {
        throw new Error(
          `Wi-Fi config characteristic not found. Expected UUID: ${WIFI_CONFIG_CHARACTERISTIC_UUID}`
        );
      }

      if (!wifiStatusChar) {
        throw new Error(
          `Wi-Fi status characteristic not found. Expected UUID: ${WIFI_STATUS_CHARACTERISTIC_UUID}`
        );
      }

      console.log("Found Wi-Fi characteristics");

      // Store references
      this.connectedDevice = deviceWithServices;
      this.wifiConfigCharacteristic = wifiConfigChar;
      this.wifiStatusCharacteristic = wifiStatusChar;

      // Subscribe to status notifications
      await this.subscribeToStatusNotifications();

      console.log("Successfully connected and subscribed to status updates");
    } catch (error) {
      console.error("Error connecting to device:", error);
      // Clean up on error
      await this.disconnect().catch(() => {
        // Ignore cleanup errors
      });
      throw error;
    }
  }

  /**
   * Subscribe to wifi_status characteristic notifications
   */
  private async subscribeToStatusNotifications(): Promise<void> {
    if (!this.wifiStatusCharacteristic) {
      throw new Error("Wi-Fi status characteristic not available");
    }

    // Read initial status
    try {
      const initialStatus = await this.wifiStatusCharacteristic.read();
      const statusValue = this.parseStatusValue(initialStatus.value);
      console.log("Initial Wi-Fi status:", statusValue);
      this.currentStatus = statusValue;
      this.notifyStatusChange(statusValue);
    } catch (error) {
      console.warn("Failed to read initial status:", error);
    }

    // Subscribe to notifications
    const subscription = this.wifiStatusCharacteristic.monitor(
      (error: BleError | null, characteristic: Characteristic | null) => {
        if (error) {
          console.error("Status notification error:", error);
          return;
        }

        if (characteristic) {
          const statusValue = this.parseStatusValue(characteristic.value);
          console.log("Wi-Fi status changed:", statusValue);
          this.currentStatus = statusValue;
          this.notifyStatusChange(statusValue);
        }
      }
    );

    this.statusSubscription = subscription;
    console.log("Subscribed to Wi-Fi status notifications");
  }

  /**
   * Parse status value from characteristic
   */
  private parseStatusValue(value: string | null | undefined): WifiStatus {
    if (!value) {
      return "idle";
    }

    const normalized = value.trim().toLowerCase();
    if (
      normalized === "idle" ||
      normalized === "connecting" ||
      normalized === "connected" ||
      normalized === "failed"
    ) {
      return normalized as WifiStatus;
    }

    console.warn("Unknown status value:", value);
    return "idle";
  }

  /**
   * Notify all registered callbacks of status change
   */
  private notifyStatusChange(status: WifiStatus): void {
    this.statusChangeCallbacks.forEach((callback) => {
      try {
        callback(status);
      } catch (error) {
        console.error("Error in status change callback:", error);
      }
    });
  }

  /**
   * Send Wi-Fi configuration to the robot
   * Serializes { ssid, password } as JSON and writes to wifi_config characteristic
   */
  async sendWifiConfig(ssid: string, password: string): Promise<void> {
    console.log("Sending Wi-Fi config:", {
      ssid: ssid.substring(0, 3) + "...",
    });

    if (!this.wifiConfigCharacteristic) {
      throw new Error("Not connected to ROVY device");
    }

    if (!ssid || !ssid.trim()) {
      throw new Error("SSID cannot be empty");
    }

    // Serialize as JSON
    const config = {
      ssid: ssid.trim(),
      password: password || "",
    };

    const jsonString = JSON.stringify(config);
    console.log("Wi-Fi config JSON:", jsonString);

    // Convert to base64 (react-native-ble-plx expects base64 encoded strings)
    // React Native doesn't have Buffer, so we use btoa or a polyfill
    // For React Native, we can use a simple base64 encoder
    const base64Value = this.stringToBase64(jsonString);

    try {
      // Write to characteristic
      await this.wifiConfigCharacteristic.writeWithResponse(base64Value);
      console.log("Wi-Fi config written successfully");

      // Status updates will come via notifications
    } catch (error) {
      console.error("Error writing Wi-Fi config:", error);
      throw new Error(
        `Failed to send Wi-Fi configuration: ${
          error instanceof Error ? error.message : "Unknown error"
        }`
      );
    }
  }

  /**
   * Register a callback for Wi-Fi status changes
   * Returns an unsubscribe function
   */
  onStatusChange(callback: StatusChangeCallback): () => void {
    this.statusChangeCallbacks.add(callback);

    // Immediately call with current status if available
    if (this.currentStatus) {
      try {
        callback(this.currentStatus);
      } catch (error) {
        console.error("Error in initial status callback:", error);
      }
    }

    // Return unsubscribe function
    return () => {
      this.statusChangeCallbacks.delete(callback);
    };
  }

  /**
   * Convert string to base64 (React Native compatible)
   * Uses UTF-8 encoding and converts to base64
   */
  private stringToBase64(str: string): string {
    // Use btoa if available (web), otherwise use a polyfill
    if (typeof btoa !== "undefined") {
      // btoa expects Latin-1, so we need to encode UTF-8 properly
      try {
        return btoa(
          encodeURIComponent(str).replace(/%([0-9A-F]{2})/g, (match, p1) => {
            return String.fromCharCode(Number.parseInt(p1, 16));
          })
        );
      } catch {
        // Fall through to polyfill
      }
    }

    // Base64 encoder for React Native
    // Convert UTF-8 string to bytes first
    const utf8Bytes: number[] = [];
    for (let i = 0; i < str.length; i++) {
      let charCode = str.charCodeAt(i);
      if (charCode < 0x80) {
        utf8Bytes.push(charCode);
      } else if (charCode < 0x800) {
        utf8Bytes.push(0xc0 | (charCode >> 6));
        utf8Bytes.push(0x80 | (charCode & 0x3f));
      } else if (charCode < 0xd800 || charCode >= 0xe000) {
        utf8Bytes.push(0xe0 | (charCode >> 12));
        utf8Bytes.push(0x80 | ((charCode >> 6) & 0x3f));
        utf8Bytes.push(0x80 | (charCode & 0x3f));
      } else {
        // Surrogate pair
        i++;
        charCode =
          0x10000 + (((charCode & 0x3ff) << 10) | (str.charCodeAt(i) & 0x3ff));
        utf8Bytes.push(0xf0 | (charCode >> 18));
        utf8Bytes.push(0x80 | ((charCode >> 12) & 0x3f));
        utf8Bytes.push(0x80 | ((charCode >> 6) & 0x3f));
        utf8Bytes.push(0x80 | (charCode & 0x3f));
      }
    }

    // Convert bytes to base64
    const chars =
      "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let output = "";
    let i = 0;

    while (i < utf8Bytes.length) {
      const a = utf8Bytes[i++];
      const b = i < utf8Bytes.length ? utf8Bytes[i++] : 0;
      const c = i < utf8Bytes.length ? utf8Bytes[i++] : 0;

      const bitmap = (a << 16) | (b << 8) | c;

      output +=
        chars.charAt((bitmap >> 18) & 63) +
        chars.charAt((bitmap >> 12) & 63) +
        (i - 2 < utf8Bytes.length ? chars.charAt((bitmap >> 6) & 63) : "=") +
        (i - 1 < utf8Bytes.length ? chars.charAt(bitmap & 63) : "=");
    }

    return output;
  }

  /**
   * Remove a status change callback
   */
  removeStatusChangeCallback(callback: StatusChangeCallback): void {
    this.statusChangeCallbacks.delete(callback);
  }

  /**
   * Get current Wi-Fi status
   */
  getCurrentStatus(): WifiStatus {
    return this.currentStatus;
  }

  /**
   * Provide reason why BLE is unavailable (if any)
   */
  getBleUnavailableReason(): string | null {
    return this.bleUnavailableReason;
  }

  /**
   * Check if connected to a device
   */
  isConnected(): boolean {
    return this.connectedDevice !== null;
  }

  /**
   * Disconnect from the robot and clean up
   */
  async disconnect(): Promise<void> {
    console.log("Disconnecting from device...");

    // Unsubscribe from notifications
    if (this.statusSubscription) {
      try {
        this.statusSubscription.remove();
        console.log("Unsubscribed from status notifications");
      } catch (error) {
        console.warn("Error removing status subscription:", error);
      }
      this.statusSubscription = null;
    }

    // Clear callbacks
    this.statusChangeCallbacks.clear();

    // Disconnect device
    if (this.connectedDevice) {
      try {
        await this.connectedDevice.cancelConnection();
        console.log("Disconnected from device");
      } catch (error) {
        console.warn("Error disconnecting device:", error);
      }
      this.connectedDevice = null;
    }

    // Clear characteristic references
    this.wifiConfigCharacteristic = null;
    this.wifiStatusCharacteristic = null;
    this.currentStatus = "idle";

    console.log("Disconnection complete");
  }

  /**
   * Cleanup - call this when the manager is no longer needed
   */
  destroy(): void {
    console.log("Destroying BLE manager...");
    this.disconnect().catch(() => {
      // Ignore errors during cleanup
    });
    if (this.bleManager) {
      this.bleManager.destroy();
    }
  }
}

// Export a singleton instance (optional - can also create new instances)
let rovyBleManagerInstance: RovyBleManager | null = null;

export function getRovyBleManager(): RovyBleManager {
  if (!rovyBleManagerInstance) {
    rovyBleManagerInstance = new RovyBleManager();
  }
  return rovyBleManagerInstance;
}
