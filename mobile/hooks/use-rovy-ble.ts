import { useCallback, useEffect, useRef, useState } from "react";

import type {
  DeviceFoundCallback,
  RovyDevice,
  StatusChangeCallback,
  WifiStatus,
} from "@/services/rovy-ble";
import { getRovyBleManager, RovyBleManager } from "@/services/rovy-ble";

/**
 * React hook for ROVY BLE Wi-Fi configuration
 * Provides high-level methods for scanning, connecting, and configuring Wi-Fi
 */
export function useRovyBle() {
  const managerRef = useRef<RovyBleManager | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isSendingConfig, setIsSendingConfig] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [wifiStatus, setWifiStatus] = useState<WifiStatus>("idle");
  const [error, setError] = useState<string | null>(null);

  // Initialize manager
  useEffect(() => {
    managerRef.current = getRovyBleManager();

    const availabilityError = managerRef.current.getBleUnavailableReason();
    if (availabilityError) {
      setError(availabilityError);
    }

    // Subscribe to status changes
    const statusCallback: StatusChangeCallback = (status) => {
      setWifiStatus(status);
    };

    managerRef.current.onStatusChange(statusCallback);

    // Check initial connection state
    setIsConnected(managerRef.current.isConnected());
    setWifiStatus(managerRef.current.getCurrentStatus());

    // Cleanup on unmount
    return () => {
      if (managerRef.current) {
        managerRef.current.removeStatusChangeCallback(statusCallback);
        // Note: We don't disconnect here as the manager might be used elsewhere
        // Call disconnect() explicitly when needed
      }
    };
  }, []);

  /**
   * Scan for nearby ROVY devices
   * @param onDeviceFound Optional callback that gets called when a device is found during scanning
   */
  const scanForRovy = useCallback(
    async (onDeviceFound?: DeviceFoundCallback): Promise<RovyDevice[]> => {
      if (!managerRef.current) {
        throw new Error("BLE manager not initialized");
      }

      setIsScanning(true);
      setError(null);

      try {
        const devices = await managerRef.current.scanForRovy(onDeviceFound);
        console.log(`Found ${devices.length} ROVY device(s)`);
        return devices;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to scan for devices";
        setError(errorMessage);
        console.error("Scan error:", err);
        throw err;
      } finally {
        setIsScanning(false);
      }
    },
    []
  );

  /**
   * Connect to a ROVY device
   */
  const connectToRovy = useCallback(async (deviceId: string): Promise<void> => {
    if (!managerRef.current) {
      throw new Error("BLE manager not initialized");
    }

    setIsConnecting(true);
    setError(null);

    try {
      await managerRef.current.connectToRovy(deviceId);
      setIsConnected(true);
      console.log("Connected to device:", deviceId);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to connect to device";
      setError(errorMessage);
      setIsConnected(false);
      console.error("Connection error:", err);
      throw err;
    } finally {
      setIsConnecting(false);
    }
  }, []);

  /**
   * Send Wi-Fi configuration
   */
  const sendWifiConfig = useCallback(
    async (ssid: string, password: string): Promise<void> => {
      if (!managerRef.current) {
        throw new Error("BLE manager not initialized");
      }

      setIsSendingConfig(true);
      setError(null);

      try {
        await managerRef.current.sendWifiConfig(ssid, password);
        console.log("Wi-Fi config sent successfully");
        // Status updates will come via notifications
      } catch (err) {
        const errorMessage =
          err instanceof Error
            ? err.message
            : "Failed to send Wi-Fi configuration";
        setError(errorMessage);
        console.error("Send config error:", err);
        throw err;
      } finally {
        setIsSendingConfig(false);
      }
    },
    []
  );

  /**
   * Disconnect from the robot
   */
  const disconnect = useCallback(async (): Promise<void> => {
    if (!managerRef.current) {
      return;
    }

    setError(null);

    try {
      await managerRef.current.disconnect();
      setIsConnected(false);
      setWifiStatus("idle");
      console.log("Disconnected from device");
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to disconnect";
      setError(errorMessage);
      console.error("Disconnect error:", err);
      throw err;
    }
  }, []);

  /**
   * Register a status change callback
   */
  const onStatusChange = useCallback((callback: StatusChangeCallback) => {
    if (!managerRef.current) {
      return () => {};
    }

    managerRef.current.onStatusChange(callback);
    return () => {
      if (managerRef.current) {
        managerRef.current.removeStatusChangeCallback(callback);
      }
    };
  }, []);

  return {
    // State
    isScanning,
    isConnecting,
    isSendingConfig,
    isConnected,
    wifiStatus,
    error,

    // Methods
    scanForRovy,
    connectToRovy,
    sendWifiConfig,
    disconnect,
    onStatusChange,
  };
}
