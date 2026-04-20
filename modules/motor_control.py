"""
Motor Control Module for Custom AI Rover Platform
Owner: Dilmurod

This module handles all physical movement according to the API contract.
Implements 4WD UGV chassis control with independent wheel control for superior maneuverability.
"""

import logging
import time
from typing import Optional

# Hardware-specific imports (uncomment when running on Jetson)
# import Jetson.GPIO as GPIO
# import RPi.GPIO as GPIO  # Alternative for Raspberry Pi compatibility

logger = logging.getLogger(__name__)

# GPIO Pin definitions for 4WD UGV chassis (adjust based on your hardware setup)
FRONT_LEFT_PIN1 = 18   # Front left motor direction pin 1
FRONT_LEFT_PIN2 = 19   # Front left motor direction pin 2
FRONT_LEFT_PWM = 12    # Front left motor PWM (speed) pin

FRONT_RIGHT_PIN1 = 20  # Front right motor direction pin 1
FRONT_RIGHT_PIN2 = 21  # Front right motor direction pin 2
FRONT_RIGHT_PWM = 13   # Front right motor PWM (speed) pin

REAR_LEFT_PIN1 = 22    # Rear left motor direction pin 1
REAR_LEFT_PIN2 = 23    # Rear left motor direction pin 2
REAR_LEFT_PWM = 16     # Rear left motor PWM (speed) pin

REAR_RIGHT_PIN1 = 24   # Rear right motor direction pin 1
REAR_RIGHT_PIN2 = 25   # Rear right motor direction pin 2
REAR_RIGHT_PWM = 26    # Rear right motor PWM (speed) pin

# Global variables
_gpio_initialized = False
_front_left_pwm = None
_front_right_pwm = None
_rear_left_pwm = None
_rear_right_pwm = None

def setup() -> None:
    """
    Initializes all GPIO pins for 4WD motor control.
    Must be called before any other motor functions.
    Raises RuntimeError if GPIO initialization fails.
    """
    global _gpio_initialized, _front_left_pwm, _front_right_pwm, _rear_left_pwm, _rear_right_pwm
    
    logger.info("Initializing 4WD motor control GPIO pins...")
    
    try:
        # TODO: Uncomment and configure when running on actual hardware
        # GPIO.setmode(GPIO.BCM)
        # GPIO.setwarnings(False)
        
        # # Set up front left motor pins
        # GPIO.setup(FRONT_LEFT_PIN1, GPIO.OUT)
        # GPIO.setup(FRONT_LEFT_PIN2, GPIO.OUT)
        # GPIO.setup(FRONT_LEFT_PWM, GPIO.OUT)
        
        # # Set up front right motor pins
        # GPIO.setup(FRONT_RIGHT_PIN1, GPIO.OUT)
        # GPIO.setup(FRONT_RIGHT_PIN2, GPIO.OUT)
        # GPIO.setup(FRONT_RIGHT_PWM, GPIO.OUT)
        
        # # Set up rear left motor pins
        # GPIO.setup(REAR_LEFT_PIN1, GPIO.OUT)
        # GPIO.setup(REAR_LEFT_PIN2, GPIO.OUT)
        # GPIO.setup(REAR_LEFT_PWM, GPIO.OUT)
        
        # # Set up rear right motor pins
        # GPIO.setup(REAR_RIGHT_PIN1, GPIO.OUT)
        # GPIO.setup(REAR_RIGHT_PIN2, GPIO.OUT)
        # GPIO.setup(REAR_RIGHT_PWM, GPIO.OUT)
        
        # # Initialize PWM for speed control (1000 Hz frequency)
        # _front_left_pwm = GPIO.PWM(FRONT_LEFT_PWM, 1000)
        # _front_right_pwm = GPIO.PWM(FRONT_RIGHT_PWM, 1000)
        # _rear_left_pwm = GPIO.PWM(REAR_LEFT_PWM, 1000)
        # _rear_right_pwm = GPIO.PWM(REAR_RIGHT_PWM, 1000)
        
        # # Start PWM with 0% duty cycle (stopped)
        # _front_left_pwm.start(0)
        # _front_right_pwm.start(0)
        # _rear_left_pwm.start(0)
        # _rear_right_pwm.start(0)
        
        # # Ensure all motors are stopped initially
        # for pin in [FRONT_LEFT_PIN1, FRONT_LEFT_PIN2, FRONT_RIGHT_PIN1, FRONT_RIGHT_PIN2,
        #             REAR_LEFT_PIN1, REAR_LEFT_PIN2, REAR_RIGHT_PIN1, REAR_RIGHT_PIN2]:
        #     GPIO.output(pin, GPIO.LOW)
        
        _gpio_initialized = True
        logger.info("4WD motor control initialized successfully")
        
        # TEMPORARY: Simulation mode for development
        logger.warning("Running in SIMULATION mode - no actual GPIO control")
        _gpio_initialized = True
        
    except Exception as e:
        logger.error(f"Failed to initialize 4WD motor control: {e}")
        raise RuntimeError(f"4WD motor control initialization failed: {e}")

def move(front_left: int, front_right: int, rear_left: int, rear_right: int) -> None:
    """
    Sets the speed of each wheel independently for maximum maneuverability.
    
    Args:
        front_left: Speed for front left wheel (-100 to 100)
        front_right: Speed for front right wheel (-100 to 100)
        rear_left: Speed for rear left wheel (-100 to 100)
        rear_right: Speed for rear right wheel (-100 to 100)
        
    Raises:
        ValueError: If speeds are outside valid range
        RuntimeError: If GPIO is not initialized
    """
    if not _gpio_initialized:
        raise RuntimeError("Motor control not initialized. Call setup() first.")
    
    # Validate speed ranges
    speeds = [front_left, front_right, rear_left, rear_right]
    speed_names = ["front_left", "front_right", "rear_left", "rear_right"]
    
    for speed, name in zip(speeds, speed_names):
        if not (-100 <= speed <= 100):
            raise ValueError(f"{name} speed {speed} out of range [-100, 100]")
    
    logger.debug(f"Setting 4WD speeds: FL={front_left}, FR={front_right}, RL={rear_left}, RR={rear_right}")
    
    # TODO: Uncomment when running on actual hardware
    # _set_motor_speed("front_left", front_left)
    # _set_motor_speed("front_right", front_right)
    # _set_motor_speed("rear_left", rear_left)
    # _set_motor_speed("rear_right", rear_right)
    
    # TEMPORARY: Simulation mode
    if any(speed != 0 for speed in speeds):
        logger.info(f"SIMULATION: 4WD Moving - FL:{front_left}%, FR:{front_right}%, RL:{rear_left}%, RR:{rear_right}%")
    else:
        logger.info("SIMULATION: All motors stopped")

def move_simple(forward_speed: int, turn_speed: int) -> None:
    """
    Simplified movement control for basic forward/backward and turning.
    
    Args:
        forward_speed: Forward/backward speed (-100 to 100)
        turn_speed: Turning speed (-100 left to 100 right)
        
    Raises:
        ValueError: If speeds are outside valid range
        RuntimeError: If GPIO is not initialized
    """
    if not _gpio_initialized:
        raise RuntimeError("Motor control not initialized. Call setup() first.")
    
    # Validate speed ranges
    if not (-100 <= forward_speed <= 100):
        raise ValueError(f"Forward speed {forward_speed} out of range [-100, 100]")
    if not (-100 <= turn_speed <= 100):
        raise ValueError(f"Turn speed {turn_speed} out of range [-100, 100]")
    
    # Calculate individual wheel speeds
    # For 4WD: left wheels turn together, right wheels turn together
    left_speed = forward_speed - turn_speed
    right_speed = forward_speed + turn_speed
    
    # Clamp speeds to valid range
    left_speed = max(-100, min(100, left_speed))
    right_speed = max(-100, min(100, right_speed))
    
    # Apply to all wheels (front and rear move together)
    move(left_speed, right_speed, left_speed, right_speed)

def _set_motor_speed(motor: str, speed: int) -> None:
    """
    Internal function to set individual motor speed and direction.
    
    Args:
        motor: "front_left", "front_right", "rear_left", or "rear_right"
        speed: Speed from -100 to 100
    """
    # TODO: Implement actual GPIO control
    # This is a template - implement based on your motor driver
    
    motor_configs = {
        "front_left": (FRONT_LEFT_PIN1, FRONT_LEFT_PIN2, _front_left_pwm),
        "front_right": (FRONT_RIGHT_PIN1, FRONT_RIGHT_PIN2, _front_right_pwm),
        "rear_left": (REAR_LEFT_PIN1, REAR_LEFT_PIN2, _rear_left_pwm),
        "rear_right": (REAR_RIGHT_PIN1, REAR_RIGHT_PIN2, _rear_right_pwm)
    }
    
    if motor not in motor_configs:
        raise ValueError(f"Invalid motor: {motor}")
    
    pin1, pin2, pwm = motor_configs[motor]
    
    # Convert speed to PWM duty cycle (0-100)
    duty_cycle = abs(speed)
    
    if speed > 0:
        # Forward direction
        # GPIO.output(pin1, GPIO.HIGH)
        # GPIO.output(pin2, GPIO.LOW)
        pass
    elif speed < 0:
        # Reverse direction
        # GPIO.output(pin1, GPIO.LOW)
        # GPIO.output(pin2, GPIO.HIGH)
        pass
    else:
        # Stop
        # GPIO.output(pin1, GPIO.LOW)
        # GPIO.output(pin2, GPIO.LOW)
        pass
    
    # Set PWM duty cycle
    # pwm.ChangeDutyCycle(duty_cycle)

def stop() -> None:
    """
    Immediately stops all motors.
    Safe to call multiple times.
    """
    if not _gpio_initialized:
        logger.warning("Motor control not initialized, cannot stop motors")
        return
    
    logger.info("Stopping all 4WD motors")
    
    # TODO: Uncomment when running on actual hardware
    # # Stop all direction pins
    # for pin in [FRONT_LEFT_PIN1, FRONT_LEFT_PIN2, FRONT_RIGHT_PIN1, FRONT_RIGHT_PIN2,
    #             REAR_LEFT_PIN1, REAR_LEFT_PIN2, REAR_RIGHT_PIN1, REAR_RIGHT_PIN2]:
    #     GPIO.output(pin, GPIO.LOW)
    
    # # Stop all PWM
    # for pwm in [_front_left_pwm, _front_right_pwm, _rear_left_pwm, _rear_right_pwm]:
    #     if pwm:
    #         pwm.ChangeDutyCycle(0)
    
    # TEMPORARY: Simulation mode
    logger.info("SIMULATION: All 4WD motors stopped")

def cleanup() -> None:
    """
    Releases all GPIO pins safely when the program exits.
    Should be called in exception handlers and at program termination.
    """
    global _gpio_initialized, _front_left_pwm, _front_right_pwm, _rear_left_pwm, _rear_right_pwm
    
    if not _gpio_initialized:
        return
    
    logger.info("Cleaning up 4WD motor control...")
    
    try:
        # Stop all motors first
        stop()
        
        # TODO: Uncomment when running on actual hardware
        # # Stop all PWM
        # for pwm in [_front_left_pwm, _front_right_pwm, _rear_left_pwm, _rear_right_pwm]:
        #     if pwm:
        #         pwm.stop()
        
        # # Clean up GPIO
        # GPIO.cleanup()
        
        _gpio_initialized = False
        _front_left_pwm = None
        _front_right_pwm = None
        _rear_left_pwm = None
        _rear_right_pwm = None
        
        logger.info("4WD motor control cleanup complete")
        
    except Exception as e:
        logger.error(f"Error during 4WD motor control cleanup: {e}")

# Emergency stop function (can be called from anywhere)
def emergency_stop() -> None:
    """Emergency stop - immediately stops all motors regardless of state."""
    logger.warning("EMERGENCY STOP activated!")
    try:
        stop()
    except Exception as e:
        logger.error(f"Error during emergency stop: {e}")

# Test functions for development
def test_motors() -> None:
    """Test function to verify 4WD motor control is working."""
    if not _gpio_initialized:
        logger.error("Cannot test motors - not initialized")
        return
    
    logger.info("Testing 4WD motors...")
    
    # Test forward movement
    logger.info("Testing forward movement...")
    move_simple(50, 0)
    time.sleep(2)
    
    # Test turning
    logger.info("Testing left turn...")
    move_simple(0, -50)
    time.sleep(1)
    
    logger.info("Testing right turn...")
    move_simple(0, 50)
    time.sleep(1)
    
    # Test individual wheel control
    logger.info("Testing individual wheel control...")
    move(30, -30, 30, -30)  # Diagonal movement
    time.sleep(1)
    
    # Test reverse
    logger.info("Testing reverse...")
    move_simple(-30, 0)
    time.sleep(1)
    
    # Stop
    logger.info("Stopping all motors...")
    stop()
    
    logger.info("4WD motor test complete")

if __name__ == "__main__":
    # Test the module independently
    logging.basicConfig(level=logging.INFO)
    
    try:
        setup()
        test_motors()
    except KeyboardInterrupt:
        logger.info("Test interrupted")
    finally:
        cleanup()
