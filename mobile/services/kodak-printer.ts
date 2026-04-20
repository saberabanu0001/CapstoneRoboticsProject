import { PermissionsAndroid, Platform } from 'react-native';
import { BleManager, Device, Characteristic } from 'react-native-ble-plx';

/**
 * Kodak Mini 2 Era M200 Bluetooth Printer Manager
 * 
 * The Kodak Mini 2 Era M200 uses Bluetooth for communication.
 * It typically advertises as "PM-210" or similar.
 * 
 * Standard printer service UUID: 18F0 (3D Print Service)
 * Or manufacturer-specific service for photo printers
 */

// Common photo printer service UUIDs
const PRINTER_SERVICE_UUIDS = [
  '000018F0-0000-1000-8000-00805F9B34FB', // 3D Print Service
  '0000FFF0-0000-1000-8000-00805F9B34FB', // Generic manufacturer service
  '49535343-FE7D-4AE5-8FA9-9FAFD205E455', // Issc proprietary service (common in photo printers)
];

// Common characteristic UUIDs for printing
const PRINT_CHARACTERISTIC_UUIDS = [
  '000018F1-0000-1000-8000-00805F9B34FB',
  '0000FFF1-0000-1000-8000-00805F9B34FB',
  '49535343-8841-43F4-A8D4-ECBE34729BB3', // TX characteristic
];

export interface PrinterDevice {
  id: string;
  name: string;
  rssi?: number | null;
}

export class KodakPrinterManager {
  private bleManager: BleManager | null = null;
  private connectedDevice: Device | null = null;
  private printCharacteristic: Characteristic | null = null;
  private serviceUuid: string | null = null;
  private characteristicUuid: string | null = null;

  constructor() {
    try {
      if (Platform.OS === 'web') {
        console.warn('Bluetooth printing not supported on web');
        return;
      }
      this.bleManager = new BleManager();
      console.log('Kodak Printer BLE Manager initialized');
    } catch (error) {
      console.error('Failed to initialize printer BLE manager:', error);
    }
  }

  /**
   * Check and request necessary permissions
   */
  private async checkPermissions(): Promise<boolean> {
    if (Platform.OS === 'android') {
      const apiLevel = Platform.Version;
      if (apiLevel >= 31) {
        try {
          const granted = await PermissionsAndroid.requestMultiple([
            PermissionsAndroid.PERMISSIONS.BLUETOOTH_SCAN,
            PermissionsAndroid.PERMISSIONS.BLUETOOTH_CONNECT,
          ]);

          return (
            granted[PermissionsAndroid.PERMISSIONS.BLUETOOTH_SCAN] === 'granted' &&
            granted[PermissionsAndroid.PERMISSIONS.BLUETOOTH_CONNECT] === 'granted'
          );
        } catch (error) {
          console.error('Permission request failed:', error);
          return false;
        }
      }
    }
    return true;
  }

  /**
   * Ensure BLE is ready for use
   */
  private async ensureBleReady(): Promise<void> {
    if (!this.bleManager) {
      throw new Error('BLE Manager not initialized');
    }

    const state = await this.bleManager.state();
    if (state !== 'PoweredOn') {
      throw new Error(`Bluetooth is not ready. State: ${state}`);
    }
  }

  /**
   * Scan for Kodak printers
   * Looks for devices with names like "PM-210", "Mini2", "Kodak", etc.
   */
  async scanForPrinters(duration: number = 10000): Promise<PrinterDevice[]> {
    console.log('Scanning for Kodak printers...');

    if (!this.bleManager) {
      throw new Error('BLE Manager not available');
    }

    const hasPermissions = await this.checkPermissions();
    if (!hasPermissions) {
      throw new Error('Bluetooth permissions not granted');
    }

    await this.ensureBleReady();

    return new Promise((resolve, reject) => {
      if (!this.bleManager) {
        reject(new Error('BLE Manager not available'));
        return;
      }

      const foundDevices = new Map<string, PrinterDevice>();
      
      const timeout = setTimeout(() => {
        this.bleManager?.stopDeviceScan();
        console.log(`Scan completed. Found ${foundDevices.size} potential printer(s)`);
        resolve(Array.from(foundDevices.values()));
      }, duration);

      this.bleManager.startDeviceScan(
        null,
        { allowDuplicates: false },
        (error, device) => {
          if (error) {
            clearTimeout(timeout);
            this.bleManager?.stopDeviceScan();
            reject(error);
            return;
          }

          if (device?.name) {
            const name = device.name.toLowerCase();
            // Look for Kodak-related device names
            if (
              name.includes('pm-210') ||
              name.includes('mini2') ||
              name.includes('kodak') ||
              name.includes('photo') ||
              name.includes('printer') ||
              name.includes('pm210')
            ) {
              console.log('Found potential printer:', device.name, device.id);
              foundDevices.set(device.id, {
                id: device.id,
                name: device.name,
                rssi: device.rssi,
              });
            }
          }
        }
      );
    });
  }

  /**
   * Connect to a Kodak printer
   * If no deviceId provided, scans and connects to the first found printer
   */
  async connect(deviceId?: string): Promise<void> {
    console.log('Connecting to Kodak printer...');

    if (!this.bleManager) {
      throw new Error('BLE Manager not available');
    }

    await this.ensureBleReady();

    let targetDeviceId = deviceId;

    // If no device ID provided, scan for printers
    if (!targetDeviceId) {
      const printers = await this.scanForPrinters(5000);
      if (printers.length === 0) {
        throw new Error('No Kodak printers found. Make sure the printer is on and nearby.');
      }
      targetDeviceId = printers[0].id;
      console.log('Auto-connecting to:', printers[0].name);
    }

    try {
      // Connect to device
      const device = await this.bleManager.connectToDevice(targetDeviceId);
      console.log('Connected to printer:', device.name);

      // Discover services and characteristics
      const deviceWithServices = await device.discoverAllServicesAndCharacteristics();
      console.log('Discovered services and characteristics');

      // Find printer service and characteristic
      const services = await deviceWithServices.services();
      console.log(`Found ${services.length} service(s)`);

      let foundService = null;
      let foundCharacteristic = null;

      // Try each known service UUID
      for (const service of services) {
        console.log('Service:', service.uuid);
        
        const characteristics = await service.characteristics();
        console.log(`  ${characteristics.length} characteristic(s)`);

        for (const char of characteristics) {
          console.log('  Characteristic:', char.uuid, 'writable:', char.isWritableWithResponse || char.isWritableWithoutResponse);
          
          // Look for writable characteristic
          if (char.isWritableWithResponse || char.isWritableWithoutResponse) {
            foundService = service;
            foundCharacteristic = char;
            this.serviceUuid = service.uuid;
            this.characteristicUuid = char.uuid;
            break;
          }
        }

        if (foundCharacteristic) break;
      }

      if (!foundCharacteristic) {
        throw new Error('Could not find writable characteristic for printing');
      }

      console.log(`Using service ${this.serviceUuid} and characteristic ${this.characteristicUuid}`);

      this.connectedDevice = deviceWithServices;
      this.printCharacteristic = foundCharacteristic;

      console.log('Printer ready for printing');
    } catch (error) {
      await this.disconnect();
      throw error;
    }
  }

  /**
   * Check if connected to printer
   */
  isConnected(): boolean {
    return this.connectedDevice !== null && this.printCharacteristic !== null;
  }

  /**
   * Print a photo
   * @param imageBase64 Base64 encoded JPEG image
   */
  async print(imageBase64: string): Promise<void> {
    console.log('Printing photo...');

    if (!this.printCharacteristic || !this.connectedDevice) {
      throw new Error('Printer not connected');
    }

    try {
      // The Kodak Mini 2 typically expects images in a specific format
      // This is a simplified implementation - actual protocol may vary
      
      // For Kodak Mini 2, images should be:
      // - JPEG format
      // - 1280x1920 pixels (for 2.1x3.4" print)
      // - Sent in chunks via BLE
      
      const chunkSize = 512; // BLE MTU size (may need adjustment)
      const imageData = this.base64ToBytes(imageBase64);
      
      console.log(`Image size: ${imageData.length} bytes`);
      console.log(`Sending in ${Math.ceil(imageData.length / chunkSize)} chunks`);

      // Send print start command (protocol-specific, may need adjustment)
      const startCommand = new Uint8Array([0x1B, 0x40]); // ESC @ - Initialize printer (generic command)
      await this.writeData(startCommand);
      
      // Wait a bit for printer to initialize
      await this.delay(100);

      // Send image data in chunks
      for (let i = 0; i < imageData.length; i += chunkSize) {
        const chunk = imageData.slice(i, Math.min(i + chunkSize, imageData.length));
        await this.writeData(chunk);
        
        // Small delay between chunks to avoid overwhelming the printer
        await this.delay(50);
        
        // Progress logging
        const progress = Math.round((i / imageData.length) * 100);
        if (progress % 10 === 0) {
          console.log(`Print progress: ${progress}%`);
        }
      }

      // Send print end command
      const endCommand = new Uint8Array([0x1B, 0x64, 0x01]); // ESC d 1 - Print and feed
      await this.writeData(endCommand);

      console.log('Print job sent successfully');
    } catch (error) {
      console.error('Print failed:', error);
      throw new Error(`Failed to print: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Write data to printer characteristic
   */
  private async writeData(data: Uint8Array): Promise<void> {
    if (!this.printCharacteristic) {
      throw new Error('Print characteristic not available');
    }

    const base64Data = this.bytesToBase64(data);
    
    // Try with response first, fall back to without response
    try {
      await this.printCharacteristic.writeWithResponse(base64Data);
    } catch (error) {
      // If writeWithResponse fails, try writeWithoutResponse
      if (this.printCharacteristic.isWritableWithoutResponse) {
        await this.printCharacteristic.writeWithoutResponse(base64Data);
      } else {
        throw error;
      }
    }
  }

  /**
   * Convert base64 string to byte array
   */
  private base64ToBytes(base64: string): Uint8Array {
    const binaryString = atob(base64);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }
    return bytes;
  }

  /**
   * Convert byte array to base64 string
   */
  private bytesToBase64(bytes: Uint8Array): string {
    let binary = '';
    for (let i = 0; i < bytes.length; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }

  /**
   * Delay helper
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Disconnect from printer
   */
  async disconnect(): Promise<void> {
    console.log('Disconnecting from printer...');

    if (this.connectedDevice) {
      try {
        await this.connectedDevice.cancelConnection();
        console.log('Disconnected from printer');
      } catch (error) {
        console.warn('Error disconnecting:', error);
      }
    }

    this.connectedDevice = null;
    this.printCharacteristic = null;
    this.serviceUuid = null;
    this.characteristicUuid = null;
  }

  /**
   * Cleanup resources
   */
  destroy(): void {
    this.disconnect();
    if (this.bleManager) {
      this.bleManager.destroy();
    }
  }
}

