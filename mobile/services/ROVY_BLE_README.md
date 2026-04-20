# ROVY BLE Wi-Fi Configuration Module

This module provides functionality to connect to ROVY robots via Bluetooth Low Energy (BLE) and configure their Wi-Fi settings.

## Files

- **`services/rovy-ble.ts`**: Core BLE manager class (`RovyBleManager`)
- **`hooks/use-rovy-ble.ts`**: React hook wrapper for easy integration
- **`components/WifiProvisionScreen.tsx`**: Example UI component demonstrating usage

## Features

### Core Functionality

1. **Scan for JARVIS devices** - Scans for BLE devices with names starting with "JARVIS"
2. **Connect to device** - Establishes BLE connection and discovers services/characteristics
3. **Send Wi-Fi configuration** - Sends SSID and password as JSON to the robot
4. **Monitor Wi-Fi status** - Subscribes to status notifications ("idle", "connecting", "connected", "failed")
5. **Disconnect** - Gracefully disconnects and cleans up resources

### BLE Service & Characteristics

- **Service UUID**: `1234abcd-0000-1000-8000-00805f9b34fb`
- **Wi-Fi Config Characteristic** (Write): `1234abcd-0001-1000-8000-00805f9b34fb`
- **Wi-Fi Status Characteristic** (Read + Notify): `1234abcd-0002-1000-8000-00805f9b34fb`

## Usage

### Using the Hook (Recommended)

```typescript
import { useRovyBle } from "@/hooks/use-rovy-ble";

function MyComponent() {
  const {
    isScanning,
    isConnecting,
    isSendingConfig,
    isConnected,
    wifiStatus,
    error,
    scanForRovy,
    connectToRovy,
    sendWifiConfig,
    disconnect,
  } = useRovyBle();

  // Scan for devices
  const handleScan = async () => {
    const devices = await scanForRovy();
    console.log("Found devices:", devices);
  };

  // Connect to a device
  const handleConnect = async (deviceId: string) => {
    await connectToRovy(deviceId);
  };

  // Send Wi-Fi config
  const handleSendConfig = async () => {
    await sendWifiConfig("MyWiFi", "password123");
  };
}
```

### Using the Manager Directly

```typescript
import { getRovyBleManager } from "@/services/rovy-ble";

const manager = getRovyBleManager();

// Scan
const devices = await manager.scanForRovy();

// Connect
await manager.connectToRovy(devices[0].id);

// Subscribe to status changes
const unsubscribe = manager.onStatusChange((status) => {
  console.log("Wi-Fi status:", status);
});

// Send config
await manager.sendWifiConfig("MyWiFi", "password123");

// Disconnect
await manager.disconnect();
unsubscribe();
```

## Permissions

### iOS
Add to `Info.plist`:
```xml
<key>NSBluetoothAlwaysUsageDescription</key>
<string>This app needs Bluetooth to connect to ROVY robots.</string>
```

### Android
The module automatically requests:
- **Android 12+**: `BLUETOOTH_SCAN` and `BLUETOOTH_CONNECT`
- **Android < 12**: `ACCESS_FINE_LOCATION` (required for BLE scanning)

## Wi-Fi Status Values

- `"idle"` - Initial state, no connection attempt
- `"connecting"` - Robot is attempting to connect to Wi-Fi
- `"connected"` - Robot successfully connected to Wi-Fi
- `"failed"` - Connection attempt failed

## Error Handling

All methods throw errors that should be caught:

```typescript
try {
  await connectToRovy(deviceId);
} catch (error) {
  console.error("Connection failed:", error);
  // Handle error (show alert, etc.)
}
```

Common errors:
- "BLE manager not available" - BLE library not installed
- "Bluetooth is turned off" - Bluetooth disabled on device
- "Bluetooth permissions not granted" - User denied permissions
- "Wi-Fi service not found" - Device doesn't expose expected service
- "Not connected to device" - Attempted operation without connection

## Example Component

See `components/WifiProvisionScreen.tsx` for a complete example implementation with:
- Device scanning UI
- Device selection
- Wi-Fi configuration form
- Status display
- Error handling

## Notes

- The module uses a singleton pattern by default (`getRovyBleManager()`)
- Status updates are delivered via notifications from the robot
- Wi-Fi configuration is sent as JSON: `{ ssid: string, password: string }`
- The module handles UTF-8 to base64 encoding for BLE transmission
- All BLE operations include console logging for debugging

