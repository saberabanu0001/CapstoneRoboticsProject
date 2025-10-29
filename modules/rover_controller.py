import serial
import time

class Rover:
    """
    Simple high-level controller for an ESP32-based UGV rover.

    Supports movement commands like forward, backward, left, right
    with configurable distance (m) and speed (slow/medium/fast).
    """

    def __init__(self, port='/dev/tty.usbmodem58FA0943761', baudrate=115200, timeout=1):
        self.ser = serial.Serial(port, baudrate, timeout=timeout)
        time.sleep(2)  # wait for the serial connection to initialize
        self.speeds = {'slow': 0.1, 'medium': 0.2, 'fast': 0.4}
        print(f"[Rover] Connected on {port} at {baudrate} baud.")

    def _send(self, L, R):
        """Send a single JSON movement command to the rover."""
        cmd = f'{{"T":1,"L":{L:.2f},"R":{R:.2f}}}\r\n'
        self.ser.write(cmd.encode())

    def _stop(self):
        """Send stop command."""
        self.ser.write(b'{"T":1,"L":0,"R":0}\r\n')

    def move(self, direction, distance_m=0.5, speed_label='medium'):
        """
        Move the rover in a given direction for a set distance and speed.

        Args:
            direction (str): 'forward', 'backward', 'left', or 'right'
            distance_m (float): distance to move in meters (approx)
            speed_label (str): 'slow', 'medium', or 'fast'
        """
        if speed_label not in self.speeds:
            raise ValueError("Speed must be 'slow', 'medium', or 'fast'")

        speed = self.speeds[speed_label]
        duration = distance_m / speed if speed > 0 else 0

        # Map directions to left/right wheel speeds
        if direction == 'forward':
            L, R = speed, speed
        elif direction == 'backward':
            L, R = -speed, -speed
        elif direction == 'left':
            L, R = -speed, speed
        elif direction == 'right':
            L, R = speed, -speed
        else:
            print(f"[Rover] Invalid direction '{direction}'")
            return

        print(f"[Rover] Moving {direction} for {distance_m:.2f} m at {speed_label} speed...")

        # Send command repeatedly (10 Hz) to maintain motion
        start = time.time()
        while time.time() - start < duration:
            self._send(L, R)
            time.sleep(0.1)

        # Stop after the duration
        self._stop()
        print("[Rover] Movement complete. Stopped.")

    def stop(self):
        """Manually stop the rover."""
        self._stop()
        print("[Rover] Emergency stop.")

    def cleanup(self):
        """Release serial port safely."""
        self._stop()
        self.ser.close()
        print("[Rover] Serial connection closed.")

