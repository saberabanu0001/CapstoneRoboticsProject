"""
Rover Controller - Serial communication with ESP32 rover
Ported from main branch rover_controller.py
"""
import serial
import time
import json
import queue
import threading
import subprocess


class Rover:
    """High-level controller for the ESP32 UGV rover."""
    
    def __init__(self, port='/dev/ttyACM0', baudrate=115200, timeout=1):
        self.ser = serial.Serial(port, baudrate, timeout=timeout)
        time.sleep(2)  # Wait for serial to initialize
        
        self.speeds = {'slow': 0.2, 'medium': 0.4, 'fast': 0.7}
        self.last_status = {}
        self.command_queue = queue.Queue()
        
        self.command_thread = threading.Thread(target=self._process_commands, daemon=True)
        self.command_thread.start()
        
        print(f"[Rover] Connected on {port}")
        self.lights_ctrl(0, 0)  # Lights off on startup
    
    def _process_commands(self):
        """Process command queue in background thread."""
        while True:
            data = self.command_queue.get()
            try:
                self.ser.write((json.dumps(data) + '\n').encode("utf-8"))
            except Exception as e:
                print(f"[Rover] Command error: {e}")
    
    def send_command(self, data):
        """Queue a command to send to rover."""
        self.command_queue.put(data)
    
    def _send_direct(self, L, R):
        """Send direct wheel command."""
        cmd = f'{{"T":1,"L":{L:.2f},"R":{R:.2f}}}\r\n'
        self.ser.write(cmd.encode())
    
    def move(self, direction, distance_m=0.5, speed_label='medium'):
        """Move rover in a direction for specified distance."""
        if speed_label not in self.speeds:
            speed_label = 'medium'
        
        speed = self.speeds[speed_label]
        duration = distance_m / speed if speed > 0 else 0
        
        if direction == 'forward':
            L, R = speed, speed
        elif direction == 'backward':
            L, R = -speed, -speed
        elif direction == 'left':
            L, R = -speed, speed
        elif direction == 'right':
            L, R = speed, -speed
        elif direction == 'stop':
            self.stop()
            return
        else:
            print(f"[Rover] Unknown direction: {direction}")
            return
        
        print(f"[Rover] Moving {direction} for {distance_m:.2f}m at {speed_label}")
        
        start = time.time()
        while time.time() - start < duration:
            self._send_direct(L, R)
            time.sleep(0.1)
        
        self.stop()
    
    def stop(self):
        """Stop the rover."""
        self.ser.write(b'{"T":1,"L":0,"R":0}\r\n')
    
    def gimbal_ctrl(self, x, y, speed=200, acceleration=10):
        """Control gimbal position."""
        data = {"T": 133, "X": x, "Y": y, "SPD": speed, "ACC": acceleration}
        self.send_command(data)
    
    def gimbal_move(self, x, y, speed_x=300, speed_y=300):
        """Move gimbal to position."""
        data = {"T": 134, "X": x, "Y": y, "SX": speed_x, "SY": speed_y}
        self.ser.write((json.dumps(data) + '\n').encode("utf-8"))
    
    def nod_yes(self, times=3):
        """Nod up and down (yes gesture)."""
        self.gimbal_ctrl(0, 0, 0, 0)
        time.sleep(0.5)
        
        for _ in range(times):
            self.gimbal_ctrl(0, -30, 0, 0)
            time.sleep(0.3)
            self.gimbal_ctrl(0, 30, 0, 0)
            time.sleep(0.3)
        
        self.gimbal_ctrl(0, 0, 0, 0)
    
    def shake_no(self, times=3):
        """Shake left and right (no gesture)."""
        self.gimbal_ctrl(0, 0, 0, 0)
        time.sleep(0.5)
        
        for _ in range(times):
            self.gimbal_ctrl(-30, 0, 0, 0)
            time.sleep(0.3)
            self.gimbal_ctrl(30, 0, 0, 0)
            time.sleep(0.3)
        
        self.gimbal_ctrl(0, 0, 0, 0)
    
    def dance(self, style='party', duration=10):
        """
        Perform a dance routine!
        
        Args:
            style: 'party' (energetic spinning), 'wiggle' (side-to-side), 'spin' (360 spins)
            duration: How long to dance in seconds
        """
        print(f"[Rover] 💃 Starting {style} dance for {duration}s!")
        
        start_time = time.time()
        
        if style == 'party':
            # Party dance - spin, move, lights!
            while time.time() - start_time < duration:
                # Flash lights
                self.lights_ctrl(255, 0)
                
                # Spin right
                self._send_direct(0.5, -0.5)
                time.sleep(0.3)
                
                self.lights_ctrl(0, 255)
                
                # Spin left
                self._send_direct(-0.5, 0.5)
                time.sleep(0.3)
                
                # Head shake
                self.gimbal_ctrl(-20, 10, 0, 0)
                time.sleep(0.2)
                self.gimbal_ctrl(20, -10, 0, 0)
                time.sleep(0.2)
                
                # Forward wiggle
                self._send_direct(0.3, 0.4)
                time.sleep(0.2)
                self._send_direct(0.4, 0.3)
                time.sleep(0.2)
        
        elif style == 'wiggle':
            # Wiggle dance - side to side with head movements
            while time.time() - start_time < duration:
                # Wiggle left
                self._send_direct(-0.3, 0.3)
                self.gimbal_ctrl(-30, 0, 0, 0)
                self.lights_ctrl(255, 0)
                time.sleep(0.4)
                
                # Wiggle right
                self._send_direct(0.3, -0.3)
                self.gimbal_ctrl(30, 0, 0, 0)
                self.lights_ctrl(0, 255)
                time.sleep(0.4)
                
                # Center and nod
                self.gimbal_ctrl(0, 20, 0, 0)
                time.sleep(0.2)
                self.gimbal_ctrl(0, -20, 0, 0)
                time.sleep(0.2)
        
        elif style == 'spin':
            # Spin dance - continuous 360 spins with lights
            while time.time() - start_time < duration:
                # Alternating light patterns
                self.lights_ctrl(255, 255)
                
                # Full spin
                self._send_direct(0.6, -0.6)
                time.sleep(1.0)
                
                self.lights_ctrl(0, 0)
                time.sleep(0.1)
                
                # Opposite spin
                self._send_direct(-0.6, 0.6)
                time.sleep(1.0)
                
                # Head movement during spin
                self.gimbal_ctrl(0, 30, 0, 0)
                time.sleep(0.2)
        
        # End dance - stop and reset
        self.stop()
        self.gimbal_ctrl(0, 0, 0, 0)
        self.lights_ctrl(0, 0)
        print("[Rover] 💃 Dance complete!")
    
    def lights_ctrl(self, front, back):
        """Control LED lights (0-255)."""
        data = {"T": 132, "IO4": front, "IO5": back}
        self.send_command(data)
    
    def display_text(self, line, text):
        """Display text on OLED (4 lines, 0-3)."""
        if 0 <= line <= 3:
            data = {"T": 3, "lineNum": line, "Text": str(text)[:21]}
            self.send_command(data)
    
    def display_lines(self, lines):
        """Display multiple lines on OLED."""
        for i, text in enumerate(lines[:4]):
            self.display_text(i, text)
    
    def get_status(self):
        """Get rover status (battery, IMU, etc.)."""
        self.ser.write(b'{"T":130}\r\n')
        time.sleep(0.3)
        
        for _ in range(5):
            if self.ser.in_waiting > 0:
                try:
                    line = self.ser.readline().decode('utf-8').strip()
                    if line:
                        data = json.loads(line)
                        if data.get('T') == 1001:
                            self.last_status = data
                            return {
                                'voltage': data.get('v', 0.0),
                                'temperature': data.get('temp', 0.0),
                                'roll': data.get('r', 0.0),
                                'pitch': data.get('p', 0.0),
                                'yaw': data.get('y', 0.0),
                            }
                except:
                    pass
            time.sleep(0.05)
        
        return self.last_status
    
    def voltage_to_percent(self, voltage):
        """Convert battery voltage to percentage."""
        if voltage is None:
            return 0
        empty, full = 9.0, 12.6
        percent = (voltage - empty) / (full - empty)
        return int(max(0, min(100, percent * 100)))
    
    def cleanup(self):
        """Clean up resources."""
        self.stop()
        self.ser.close()
        print("[Rover] Disconnected")


# Test
if __name__ == "__main__":
    rover = Rover()
    print("Status:", rover.get_status())
    rover.display_lines(["ROVY", "Cloud Mode", "Connecting...", ""])
    time.sleep(2)
    rover.cleanup()

