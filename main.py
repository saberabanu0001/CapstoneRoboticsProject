#!/usr/bin/env python3
"""
Custom AI Rover Platform - Main Program
Capstone Design Project

This is the main orchestration file that coordinates all modules
according to the API contract defined in README.md.
"""

import sys
import signal
import time
import logging
from typing import Optional

# Import our custom modules
try:
    import modules.motor_control as motor
    import modules.vision as vision
    import modules.audio as audio
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure all module files exist in the modules/ directory")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_rover.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class AIRoverPlatform:
    """Main class for the Custom AI Rover Platform."""
    
    def __init__(self):
        self.running = False
        self.modules_initialized = False
        
    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
        
    def initialize_modules(self) -> bool:
        """Initialize all hardware modules."""
        logger.info("Initializing AI Rover Platform modules...")
        
        try:
            # Initialize 4WD motor control
            logger.info("Setting up 4WD motor control...")
            motor.setup()
            
            # Initialize vision system
            logger.info("Setting up vision system...")
            vision.setup()
            
            # Initialize audio system
            logger.info("Setting up audio system...")
            audio.setup()
            
            self.modules_initialized = True
            logger.info("All AI Rover modules initialized successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize modules: {e}")
            self.cleanup_modules()
            return False
    
    def cleanup_modules(self):
        """Clean up all modules safely."""
        if not self.modules_initialized:
            return
            
        logger.info("Cleaning up modules...")
        
        try:
            motor.cleanup()
            logger.info("Motor control cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up motor control: {e}")
            
        try:
            vision.cleanup()
            logger.info("Vision system cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up vision system: {e}")
            
        try:
            audio.cleanup()
            logger.info("Audio system cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up audio system: {e}")
    
    def follow_person_behavior(self):
        """Implement person-following behavior using 4WD control."""
        if vision.is_person_detected():
            # Simple following logic - move forward when person detected
            distance = vision.get_obstacle_distance()
            
            if distance > 2.0:  # Person is far, move forward
                motor.move_simple(60, 0)
                logger.debug("Person detected - moving forward")
            elif distance > 1.0:  # Person is at good distance, slow approach
                motor.move_simple(30, 0)
                logger.debug("Person detected - slow approach")
            else:  # Too close, stop
                motor.stop()
                logger.debug("Too close to person - stopping")
        else:
            # No person detected, stop and look around
            motor.stop()
            logger.debug("No person detected - stopping")
    
    def obstacle_avoidance(self):
        """Basic obstacle avoidance behavior using 4WD control."""
        distance = vision.get_obstacle_distance()
        
        if distance < 0.5:  # Very close obstacle
            motor.stop()
            logger.warning("Obstacle very close - emergency stop")
            return True  # Signal to stop other behaviors
        elif distance < 1.0:  # Close obstacle
            # Simple avoidance - turn right using 4WD
            motor.move_simple(0, 30)
            time.sleep(0.5)
            motor.stop()
            logger.info("Obstacle detected - avoiding")
            return True
            
        return False  # No obstacle interference
    
    def handle_voice_interaction(self):
        """Handle voice commands and AI responses."""
        try:
            # Listen for voice input (non-blocking check)
            command = audio.listen_and_transcribe()
            
            if command:
                logger.info(f"Voice command received: '{command}'")
                
                # Get AI response
                response = audio.get_intelligent_response(command)
                logger.info(f"AI response: '{response}'")
                
                # Speak the response
                audio.speak(response)
                
                # Handle specific commands
                if "stop" in command.lower() or "halt" in command.lower():
                    motor.stop()
                    logger.info("Voice command: Stop")
                elif "follow" in command.lower():
                    logger.info("Voice command: Follow mode activated")
                    # Follow mode is default behavior
                    
        except Exception as e:
            logger.error(f"Error in voice interaction: {e}")
    
    def run_main_loop(self):
        """Main robot behavior loop."""
        logger.info("Starting AI Rover Platform main behavior loop...")
        self.running = True
        
        while self.running:
            try:
                # Priority 1: Obstacle avoidance (safety first)
                if self.obstacle_avoidance():
                    # If obstacle avoidance is active, skip other behaviors
                    time.sleep(0.1)
                    continue
                
                # Priority 2: Person following behavior
                self.follow_person_behavior()
                
                # Priority 3: Voice interaction (non-blocking)
                self.handle_voice_interaction()
                
                # Small delay to prevent excessive CPU usage
                time.sleep(0.05)  # 20 Hz update rate
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(1)  # Longer delay on error
    
    def run(self):
        """Main entry point for the AI rover."""
        logger.info("Starting Custom AI Rover Platform...")
        
        # Set up signal handlers
        self.setup_signal_handlers()
        
        # Initialize all modules
        if not self.initialize_modules():
            logger.error("Failed to initialize modules. Exiting.")
            return 1
        
        try:
            # Welcome message
            audio.speak("Hello! AI Rover Platform is ready for autonomous operation.")
            
            # Run main behavior loop
            self.run_main_loop()
            
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            # Clean up
            motor.stop()  # Emergency stop
            self.cleanup_modules()
            logger.info("AI Rover Platform shutdown complete")
            
        return 0

def main():
    """Entry point for the program."""
    rover = AIRoverPlatform()
    return rover.run()

if __name__ == "__main__":
    sys.exit(main())
