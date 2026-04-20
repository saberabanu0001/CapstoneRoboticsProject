#!/usr/bin/env python3
"""
WiFi Provisioning via Hotspot (Replaces Bluetooth)

If Pi has no WiFi connection:
  - Creates "ROVY-Setup" hotspot
  - Runs HTTP server on 192.168.4.1:80
  - Phone connects to hotspot and sends WiFi credentials
  - Pi connects to real WiFi and disables hotspot

If Pi already has WiFi:
  - Does nothing, exits immediately
"""
import asyncio
import json
import subprocess
import time
import socket
from typing import Dict, List, Tuple, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# Hotspot config
HOTSPOT_SSID = "ROVY-Setup"
HOTSPOT_PASSWORD = "rovysetup"  # Min 8 chars for WPA
HOTSPOT_IP = "192.168.4.1"
HOTSPOT_PORT = 80


class WifiManager:
    """
    Wrapper around nmcli for WiFi management.
    Same as original ble.py WifiManager.
    """
    
    def _run(self, args: List[str]) -> Tuple[int, str, str]:
        """Run a command and return (returncode, stdout, stderr)."""
        proc = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        out, err = proc.communicate()
        return proc.returncode, out.strip(), err.strip()
    
    def is_connected(self) -> bool:
        """Check if connected to any WiFi network."""
        code, out, _ = self._run([
            "nmcli", "-t", "-f", "TYPE,STATE", "device", "status"
        ])
        if code != 0:
            return False
        
        for line in out.splitlines():
            parts = line.split(":")
            if len(parts) >= 2:
                if parts[0] == "wifi" and parts[1] == "connected":
                    return True
        return False
    
    def scan_networks(self) -> List[Dict]:
        """Scan and return available WiFi networks."""
        self._run(["nmcli", "dev", "wifi", "rescan"])
        
        code, out, err = self._run([
            "nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY,FREQ", "dev", "wifi"
        ])
        if code != 0:
            return []
        
        networks: List[Dict] = []
        seen = set()
        
        for line in out.splitlines():
            if not line:
                continue
            parts = line.split(":")
            if len(parts) < 4:
                continue
            
            ssid = parts[0].strip()
            if not ssid or ssid in seen:
                continue
            seen.add(ssid)
            
            try:
                signal = int(parts[1].strip())
            except ValueError:
                signal = 0
            
            try:
                frequency = int(parts[3].strip())
            except ValueError:
                frequency = 0
            
            security = parts[2].strip()
            if not security or security == "--":
                security = "Open"
            
            networks.append({
                "ssid": ssid,
                "signal": signal,
                "security": security,
                "frequency": frequency
            })
        
        networks.sort(key=lambda n: n["signal"], reverse=True)
        return networks
    
    def connect(self, ssid: str, password: str) -> Dict:
        """Connect to a WiFi network."""
        ssid = ssid.strip()
        if not ssid:
            return {"success": False, "message": "SSID cannot be empty"}
        
        if password:
            args = ["nmcli", "dev", "wifi", "connect", ssid, "password", password]
        else:
            args = ["nmcli", "dev", "wifi", "connect", ssid]
        
        code, out, err = self._run(args)
        
        if code == 0:
            return {"success": True, "message": out or "Connected"}
        else:
            return {"success": False, "message": err or out or "Failed to connect"}
    
    def current_connection(self) -> Dict:
        """Get current WiFi connection info."""
        connected = False
        network_name = None
        ip_address = None
        
        code, out, _ = self._run([
            "nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "device", "status"
        ])
        
        if code == 0:
            for line in out.splitlines():
                parts = line.split(":")
                if len(parts) >= 4:
                    device_type = parts[1]
                    state = parts[2]
                    connection = parts[3]
                    
                    if device_type == "wifi" and state == "connected" and connection:
                        network_name = connection
                        connected = True
                        
                        # Get IP
                        ip_code, ip_out, _ = self._run([
                            "nmcli", "-t", "-f", "IP4.ADDRESS", "device", "show", parts[0]
                        ])
                        if ip_code == 0 and ip_out:
                            if ":" in ip_out:
                                ip_part = ip_out.split(":", 1)[1]
                                ip_address = ip_part.split("/")[0]
                        break
        
        # Fallback for IP
        if connected and not ip_address:
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip_address = s.getsockname()[0]
                s.close()
            except:
                pass
        
        return {
            "connected": connected,
            "network_name": network_name,
            "ip_address": ip_address
        }


class HotspotManager:
    """Manages WiFi hotspot creation and removal."""
    
    def __init__(self, ssid: str = HOTSPOT_SSID, password: str = HOTSPOT_PASSWORD):
        self.ssid = ssid
        self.password = password
        self.connection_name = "rovy-hotspot"
    
    def _run(self, args: List[str]) -> Tuple[int, str, str]:
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = proc.communicate()
        return proc.returncode, out.strip(), err.strip()
    
    def start(self) -> bool:
        """Start the hotspot."""
        print(f"[Hotspot] Starting '{self.ssid}'...")
        
        # Delete old hotspot connection if exists
        self._run(["nmcli", "connection", "delete", self.connection_name])
        
        # Create hotspot
        code, out, err = self._run([
            "nmcli", "device", "wifi", "hotspot",
            "ifname", "wlan0",
            "con-name", self.connection_name,
            "ssid", self.ssid,
            "password", self.password
        ])
        
        if code == 0:
            print(f"[Hotspot] ✓ Started: {self.ssid}")
            print(f"[Hotspot] Password: {self.password}")
            print(f"[Hotspot] IP: {HOTSPOT_IP}")
            return True
        else:
            print(f"[Hotspot] ✗ Failed: {err or out}")
            return False
    
    def stop(self) -> bool:
        """Stop the hotspot."""
        print("[Hotspot] Stopping...")
        code, _, _ = self._run(["nmcli", "connection", "down", self.connection_name])
        self._run(["nmcli", "connection", "delete", self.connection_name])
        return code == 0
    
    def is_active(self) -> bool:
        """Check if hotspot is running."""
        code, out, _ = self._run(["nmcli", "-t", "-f", "NAME,STATE", "connection", "show", "--active"])
        return self.connection_name in out


class ProvisioningHandler(BaseHTTPRequestHandler):
    """HTTP handler for WiFi provisioning."""
    
    wifi_manager = WifiManager()
    hotspot_manager = None
    should_stop = False
    
    def log_message(self, format, *args):
        print(f"[HTTP] {args[0]}")
    
    def send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/" or self.path == "/status":
            # Status endpoint
            status = self.wifi_manager.current_connection()
            self.send_json({
                "mode": "hotspot",
                "hotspot_ssid": HOTSPOT_SSID,
                **status
            })
        
        elif self.path == "/scan" or self.path == "/wifi/scan":
            # Scan networks
            networks = self.wifi_manager.scan_networks()
            self.send_json({"networks": networks})
        
        elif self.path == "/health":
            self.send_json({"status": "ok", "mode": "provisioning"})
        
        else:
            self.send_json({"error": "Not found"}, 404)
    
    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode() if content_length > 0 else "{}"
        
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON"}, 400)
            return
        
        if self.path == "/connect" or self.path == "/wifi/connect":
            # Connect to WiFi
            ssid = data.get("ssid", "")
            password = data.get("password", "")
            
            print(f"[Provision] Connecting to '{ssid}'...")
            
            # Stop hotspot first
            if self.hotspot_manager:
                self.hotspot_manager.stop()
            
            # Connect to WiFi
            result = self.wifi_manager.connect(ssid, password)
            
            if result["success"]:
                print(f"[Provision] ✓ Connected to '{ssid}'")
                self.send_json(result)
                # Signal to stop server
                ProvisioningHandler.should_stop = True
            else:
                print(f"[Provision] ✗ Failed: {result['message']}")
                # Restart hotspot on failure
                if self.hotspot_manager:
                    self.hotspot_manager.start()
                self.send_json(result, 400)
        
        else:
            self.send_json({"error": "Not found"}, 404)


def run_provisioning_server():
    """Run the HTTP provisioning server."""
    wifi = WifiManager()
    hotspot = HotspotManager()
    
    # Check if already connected to WiFi
    if wifi.is_connected():
        status = wifi.current_connection()
        print(f"[Provision] Already connected to WiFi: {status['network_name']}")
        print(f"[Provision] IP: {status['ip_address']}")
        print("[Provision] Hotspot not needed, exiting.")
        return True
    
    # Start hotspot
    print("[Provision] No WiFi connection, starting hotspot...")
    if not hotspot.start():
        print("[Provision] ✗ Failed to start hotspot")
        return False
    
    # Setup handler
    ProvisioningHandler.hotspot_manager = hotspot
    ProvisioningHandler.should_stop = False
    
    # Start HTTP server
    server = HTTPServer(("0.0.0.0", HOTSPOT_PORT), ProvisioningHandler)
    print(f"[Provision] HTTP server running on http://{HOTSPOT_IP}:{HOTSPOT_PORT}")
    print(f"[Provision] Connect your phone to '{HOTSPOT_SSID}' (password: {HOTSPOT_PASSWORD})")
    print("[Provision] Then open the ROVY app or visit http://192.168.4.1")
    
    # Serve until WiFi connected
    while not ProvisioningHandler.should_stop:
        server.handle_request()
    
    print("[Provision] ✓ WiFi configured, shutting down hotspot server")
    server.server_close()
    return True


async def main():
    """Main entry point."""
    print("=" * 50)
    print("  ROVY WiFi Provisioning (Hotspot Mode)")
    print("  Replaces Bluetooth - No BLE needed!")
    print("=" * 50)
    
    success = run_provisioning_server()
    
    if success:
        wifi = WifiManager()
        status = wifi.current_connection()
        if status["connected"]:
            print(f"\n✓ Connected to: {status['network_name']}")
            print(f"✓ IP Address: {status['ip_address']}")
            print("\nYou can now run the main API:")
            print("  cd ~/rovy_client/cloud && uvicorn app.main:app --host 0.0.0.0 --port 8000")


if __name__ == "__main__":
    asyncio.run(main())

