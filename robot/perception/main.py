#!/usr/bin/env python3
"""
Rovy Raspberry Pi Client
Connects to rover hardware and streams to PC server via Tailscale.

Usage:
    python main.py
"""
import asyncio
import json
import time
import base64
import signal
import sys
import threading
from datetime import datetime

import config

# Optional imports with fallbacks
try:
    import websockets
    WEBSOCKETS_OK = True
except ImportError:
    WEBSOCKETS_OK = False
    print("ERROR: websockets not installed. Run: pip install websockets")

try:
    import cv2
    CAMERA_OK = True
except ImportError:
    CAMERA_OK = False
    print("WARNING: OpenCV not installed. Camera disabled.")

try:
    import pyaudio
    import numpy as np
    AUDIO_OK = True
except ImportError:
    AUDIO_OK = False
    print("WARNING: PyAudio not installed. Microphone disabled.")

try:
    import sounddevice as sd
    import soundfile as sf
    import io
    PLAYBACK_OK = True
except ImportError:
    PLAYBACK_OK = False
    print("WARNING: sounddevice not installed. Audio playback disabled.")

try:
    from rover import Rover
    ROVER_OK = True
except Exception as e:
    ROVER_OK = False
    print(f"WARNING: Rover not available: {e}")

try:
    from wake_word_detector import WakeWordDetector
    WAKE_WORD_OK = True
except Exception as e:
    WAKE_WORD_OK = False
    print(f"WARNING: Wake word detector not available: {e}")


class RovyClient:
    """
    Client that runs on Raspberry Pi.
    - Connects to rover via serial
    - Streams audio/video to PC server
    - Receives commands from server
    """
    
    def __init__(self):
        self.running = False
        self.ws = None
        self.rover = None
        self.camera = None
        self.audio_stream = None
        self.wake_word_detector = None
        
        # State
        self.is_listening = False
        self.audio_buffer = []
        self.last_image = None
        
        print("=" * 50)
        print("  ROVY RASPBERRY PI CLIENT")
        print(f"  Server: {config.SERVER_URL}")
        print("=" * 50)
    
    def init_rover(self):
        """Initialize rover connection."""
        if not ROVER_OK:
            print("[Rover] Not available")
            return False
        
        try:
            self.rover = Rover(config.ROVER_SERIAL_PORT, config.ROVER_BAUDRATE)
            self.rover.display_lines([
                "ROVY Cloud",
                "Connecting...",
                config.PC_SERVER_IP,
                ""
            ])
            print("[Rover] Connected")
            return True
        except Exception as e:
            print(f"[Rover] Connection failed: {e}")
            return False
    
    def init_camera(self):
        """Initialize camera."""
        if not CAMERA_OK:
            return False
        
        try:
            self.camera = cv2.VideoCapture(config.CAMERA_INDEX)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
            self.camera.set(cv2.CAP_PROP_FPS, config.CAMERA_FPS)
            
            ret, _ = self.camera.read()
            if ret:
                print("[Camera] Ready")
                return True
            else:
                print("[Camera] Failed to read frame")
                return False
        except Exception as e:
            print(f"[Camera] Init failed: {e}")
            return False
    
    def init_audio(self):
        """Initialize audio input (ReSpeaker)."""
        if not AUDIO_OK:
            return False
        
        try:
            self.pyaudio = pyaudio.PyAudio()
            
            # Find ReSpeaker device
            device_index = None
            for i in range(self.pyaudio.get_device_count()):
                info = self.pyaudio.get_device_info_by_index(i)
                name = info.get('name', '').lower()
                if 'respeaker' in name or 'seeed' in name:
                    device_index = i
                    print(f"[Audio] Found ReSpeaker: {info['name']}")
                    break
            
            self.audio_device_index = device_index
            print("[Audio] Ready")
            return True
        except Exception as e:
            print(f"[Audio] Init failed: {e}")
            return False
    
    def init_wake_word_detector(self):
        """Initialize wake word detector with VAD + Whisper."""
        if not WAKE_WORD_OK:
            print("[Wake Word] Not available")
            return False
        
        try:
            print("[Wake Word] Loading Silero VAD + Whisper tiny...")
            self.wake_word_detector = WakeWordDetector(
                wake_words=config.WAKE_WORDS,
                sample_rate=config.VAD_SAMPLE_RATE,
                device_index=self.audio_device_index if hasattr(self, 'audio_device_index') else None,
                vad_threshold=config.VAD_THRESHOLD,
                whisper_model=config.WHISPER_MODEL,
                whisper_device=config.WHISPER_DEVICE,
                whisper_compute_type=config.WHISPER_COMPUTE_TYPE,
                min_speech_duration=config.VAD_MIN_SPEECH_DURATION,
                min_silence_duration=config.VAD_MIN_SILENCE_DURATION,
            )
            print(f"[Wake Word] Ready! Listening for: {config.WAKE_WORDS}")
            return True
        except Exception as e:
            print(f"[Wake Word] Init failed: {e}")
            return False
    
    async def connect_server(self):
        """Connect to PC server via WebSocket."""
        if not WEBSOCKETS_OK:
            return False
        
        attempt = 0
        while self.running:
            attempt += 1
            try:
                print(f"[Server] Connecting to {config.SERVER_URL} (attempt {attempt})...")
                
                self.ws = await websockets.connect(
                    config.SERVER_URL,
                    ping_interval=30,
                    ping_timeout=10
                )
                
                print("[Server] Connected!")
                
                if self.rover:
                    self.rover.display_lines([
                        "ROVY Cloud",
                        "Connected!",
                        config.PC_SERVER_IP,
                        datetime.now().strftime("%H:%M:%S")
                    ])
                
                return True
                
            except Exception as e:
                print(f"[Server] Connection failed: {e}")
                
                if self.rover:
                    self.rover.display_lines([
                        "ROVY Cloud",
                        "Reconnecting...",
                        f"Attempt {attempt}",
                        str(e)[:21]
                    ])
                
                if config.MAX_RECONNECT_ATTEMPTS > 0 and attempt >= config.MAX_RECONNECT_ATTEMPTS:
                    print("[Server] Max reconnect attempts reached")
                    return False
                
                await asyncio.sleep(config.RECONNECT_DELAY)
        
        return False
    
    async def send_message(self, msg_type: str, **kwargs):
        """Send a message to the server."""
        if not self.ws:
            return
        
        message = {
            "type": msg_type,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        
        try:
            await self.ws.send(json.dumps(message))
        except Exception as e:
            print(f"[Send] Error: {e}")
    
    async def handle_message(self, raw_message: str):
        """Handle incoming message from server."""
        try:
            msg = json.loads(raw_message)
            msg_type = msg.get('type', '')
            
            if msg_type == 'speak':
                await self.handle_speak(msg)
            
            elif msg_type == 'move':
                await self.handle_move(msg)
            
            elif msg_type == 'gimbal':
                await self.handle_gimbal(msg)
            
            elif msg_type == 'lights':
                await self.handle_lights(msg)
            
            elif msg_type == 'display':
                await self.handle_display(msg)
            
            elif msg_type == 'navigation':
                await self.handle_navigation(msg)
            
            elif msg_type == 'dance':
                await self.handle_dance(msg)
            
            elif msg_type == 'music':
                await self.handle_music(msg)
            
            elif msg_type == 'pong':
                pass  # Heartbeat response
            
            elif msg_type == 'error':
                print(f"[Server Error] {msg.get('error', 'Unknown error')}")
            
            else:
                print(f"[Unknown message type] {msg_type}")
                
        except json.JSONDecodeError as e:
            print(f"[Parse Error] {e}")
    
    async def handle_speak(self, msg):
        """Handle speak command - play TTS audio using Piper."""
        text = msg.get('text', '')
        audio_b64 = msg.get('audio_base64')
        
        print(f"[Speak] {text[:50]}...")
        
        if audio_b64:
            # Play pre-generated audio from server using aplay with correct device
            try:
                import subprocess
                import tempfile
                import os
                
                audio_bytes = base64.b64decode(audio_b64)
                
                # Save to temp file and play with aplay on correct device
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                    f.write(audio_bytes)
                    temp_wav = f.name
                
                # Play using aplay with configured speaker device
                subprocess.run(
                    ['aplay', '-D', config.SPEAKER_DEVICE, temp_wav],
                    capture_output=True,
                    timeout=30
                )
                os.unlink(temp_wav)
                return
            except Exception as e:
                print(f"[Speak] Server audio failed: {e}, trying Piper...")
        
        # Use Piper TTS locally on Pi
        try:
            import subprocess
            import tempfile
            import os
            
            # Piper TTS command - adjust voice path as needed
            piper_voice = getattr(config, 'PIPER_VOICE', '/usr/share/piper/en_US-lessac-medium.onnx')
            
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                wav_path = f.name
            
            # Generate speech with Piper
            proc = subprocess.run(
                ['piper', '--model', piper_voice, '--output_file', wav_path],
                input=text,
                text=True,
                capture_output=True,
                timeout=30
            )
            
            if proc.returncode == 0 and os.path.exists(wav_path):
                # Play the generated audio using aplay with correct device
                subprocess.run(
                    ['aplay', '-D', config.SPEAKER_DEVICE, wav_path],
                    capture_output=True,
                    timeout=30
                )
                os.unlink(wav_path)
            else:
                # Fallback to espeak
                print(f"[Speak] Piper failed, trying espeak...")
                subprocess.run(['espeak', text], timeout=30)
                
        except FileNotFoundError:
            # Piper not installed, use espeak
            print("[Speak] Piper not found, using espeak")
            import subprocess
            try:
                subprocess.run(['espeak', text], timeout=30)
            except:
                print(f"[Speak] No TTS available: {text}")
        except Exception as e:
            print(f"[Speak] TTS error: {e}")
    
    async def handle_move(self, msg):
        """Handle movement command."""
        if not self.rover:
            return
        
        direction = msg.get('direction', 'stop')
        distance = msg.get('distance', 0.5)
        speed = msg.get('speed', 'medium')
        
        print(f"[Move] {direction} {distance}m at {speed}")
        
        # Run movement in thread to not block
        def do_move():
            self.rover.move(direction, distance, speed)
        
        threading.Thread(target=do_move, daemon=True).start()
    
    async def handle_gimbal(self, msg):
        """Handle gimbal command."""
        if not self.rover:
            return
        
        action = msg.get('action', 'move')
        pan = msg.get('pan', 0)
        tilt = msg.get('tilt', 0)
        speed = msg.get('speed', 200)
        
        print(f"[Gimbal] {action} pan={pan} tilt={tilt}")
        
        if action == 'nod':
            threading.Thread(target=self.rover.nod_yes, daemon=True).start()
        elif action == 'shake':
            threading.Thread(target=self.rover.shake_no, daemon=True).start()
        elif action == 'reset':
            self.rover.gimbal_ctrl(0, 0, speed, 10)
        else:
            self.rover.gimbal_ctrl(pan, tilt, speed, 10)
    
    async def handle_lights(self, msg):
        """Handle lights command."""
        if not self.rover:
            return
        
        front = msg.get('front', 0)
        back = msg.get('back', 0)
        self.rover.lights_ctrl(front, back)
    
    async def handle_display(self, msg):
        """Handle OLED display command."""
        if not self.rover:
            return
        
        lines = msg.get('lines', [])
        self.rover.display_lines(lines)
    
    async def handle_navigation(self, msg):
        """Handle navigation command."""
        action = msg.get('action', 'status')
        
        print(f"[Navigation] {action}")
        
        # Import navigator dynamically when needed
        if not hasattr(self, 'navigator'):
            try:
                import sys
                import os
                # Add oakd_navigation to path
                nav_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'oakd_navigation')
                if nav_path not in sys.path:
                    sys.path.insert(0, nav_path)
                
                from rovy_integration import RovyNavigator
                self.navigator = None  # Will be initialized on start
                print("[Navigation] Module loaded")
            except Exception as e:
                print(f"[Navigation] Failed to import: {e}")
                return
        
        # Handle different navigation actions
        if action == 'start_explore':
            duration = msg.get('duration', None)
            
            def start_nav():
                try:
                    if self.navigator is None:
                        from rovy_integration import RovyNavigator
                        # Pass existing rover instance to avoid serial port conflict
                        self.navigator = RovyNavigator(rover_instance=self.rover)
                        self.navigator.start()
                    
                    print(f"[Navigation] Starting exploration (duration={duration})")
                    self.navigator.explore(duration=duration)
                except Exception as e:
                    print(f"[Navigation] Error: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Run navigation in separate thread
            threading.Thread(target=start_nav, daemon=True).start()
        
        elif action == 'stop':
            if hasattr(self, 'navigator') and self.navigator:
                def stop_nav():
                    try:
                        self.navigator.stop()
                        self.navigator.cleanup()
                        self.navigator = None
                    except Exception as e:
                        print(f"[Navigation] Stop error: {e}")
                
                threading.Thread(target=stop_nav, daemon=True).start()
        
        elif action == 'goto':
            x = msg.get('x', 0)
            y = msg.get('y', 0)
            
            def navigate_to():
                try:
                    if self.navigator is None:
                        from rovy_integration import RovyNavigator
                        # Pass existing rover instance to avoid serial port conflict
                        self.navigator = RovyNavigator(rover_instance=self.rover)
                        self.navigator.start()
                    
                    print(f"[Navigation] Navigating to ({x}, {y})")
                    self.navigator.navigate_to(x, y)
                except Exception as e:
                    print(f"[Navigation] Error: {e}")
                    import traceback
                    traceback.print_exc()
            
            threading.Thread(target=navigate_to, daemon=True).start()
    
    async def handle_dance(self, msg):
        """Handle dance command."""
        if not self.rover:
            print("[Dance] No rover instance available")
            return
        
        style = msg.get('style', 'party')
        duration = msg.get('duration', 10)
        with_music = msg.get('with_music', False)
        music_genre = msg.get('music_genre', 'dance')
        
        print(f"[Dance] 💃 Starting {style} dance for {duration}s!")
        if with_music:
            print(f"[Dance] 🎵 With {music_genre} music!")
        
        # Display on OLED
        self.rover.display_lines([
            "DANCE MODE" + (" 🎵" if with_music else ""),
            f"Style: {style}",
            f"Time: {duration}s",
            "💃🕺💃"
        ])
        
        # Run dance in separate thread
        def do_dance():
            try:
                # Start music if requested
                music_player = None
                if with_music:
                    try:
                        from music_player import get_music_player
                        music_player = get_music_player()
                        
                        if music_player and music_player.yt_music:
                            print(f"[Dance] 🎵 Starting {music_genre} music...")
                            music_player.play_random(music_genre)
                            time.sleep(2)  # Let music start
                        else:
                            print("[Dance] ⚠️ Music player not available, dancing without music")
                    except Exception as music_error:
                        print(f"[Dance] ⚠️ Music error: {music_error}, dancing without music")
                
                # Perform dance
                self.rover.dance(style=style, duration=duration)
                
                # Stop music after dance
                if music_player and music_player.is_playing:
                    print("[Dance] 🎵 Stopping music...")
                    music_player.stop()
                
                # Reset display after dance
                self.rover.display_lines([
                    "ROVY",
                    "Cloud Mode",
                    "Ready",
                    ""
                ])
            except Exception as e:
                print(f"[Dance] Error: {e}")
                import traceback
                traceback.print_exc()
        
        threading.Thread(target=do_dance, daemon=True).start()
    
    async def handle_music(self, msg):
        """Handle music playback command."""
        action = msg.get('action', 'play')
        genre = msg.get('genre', 'dance')
        
        try:
            from music_player import get_music_player
            music_player = get_music_player()
            
            if not music_player or not music_player.yt_music:
                print("[Music] ⚠️ YouTube Music not configured")
                if self.rover:
                    self.rover.display_lines([
                        "Music Error",
                        "YT Music",
                        "Not Setup",
                        ""
                    ])
                return
            
            if action == 'play':
                print(f"[Music] 🎵 Playing {genre} music...")
                
                if self.rover:
                    self.rover.display_lines([
                        "MUSIC MODE",
                        f"Genre: {genre}",
                        "Loading...",
                        "🎵"
                    ])
                
                def play_music():
                    success = music_player.play_random(genre)
                    if success and self.rover:
                        song = music_player.current_song
                        if song:
                            self.rover.display_lines([
                                "NOW PLAYING",
                                song['title'][:21],
                                song['artist'][:21],
                                "🎵"
                            ])
                    elif self.rover:
                        self.rover.display_lines([
                            "Music Error",
                            "No songs found",
                            f"Genre: {genre}",
                            ""
                        ])
                
                threading.Thread(target=play_music, daemon=True).start()
            
            elif action == 'stop':
                print("[Music] ⏹️ Stopping music...")
                music_player.stop()
                
                if self.rover:
                    self.rover.display_lines([
                        "MUSIC",
                        "Stopped",
                        "",
                        ""
                    ])
            
            elif action == 'status':
                status = music_player.get_status()
                print(f"[Music] Status: {status}")
                
        except ImportError:
            print("[Music] ⚠️ music_player module not found")
        except Exception as e:
            print(f"[Music] Error: {e}")
            import traceback
            traceback.print_exc()
    
    def capture_image(self) -> bytes:
        """Capture image from camera as JPEG bytes."""
        if not self.camera:
            return None
        
        ret, frame = self.camera.read()
        if not ret:
            return None
        
        # Encode as JPEG
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, config.JPEG_QUALITY])
        return buffer.tobytes()
    
    def record_audio(self, duration: float) -> bytes:
        """Record audio from microphone."""
        if not AUDIO_OK or not self.pyaudio:
            return None
        
        try:
            frames = []
            
            stream = self.pyaudio.open(
                format=pyaudio.paInt16,
                channels=config.CHANNELS,
                rate=config.SAMPLE_RATE,
                input=True,
                input_device_index=self.audio_device_index,
                frames_per_buffer=config.CHUNK_SIZE
            )
            
            num_chunks = int(config.SAMPLE_RATE / config.CHUNK_SIZE * duration)
            
            for _ in range(num_chunks):
                data = stream.read(config.CHUNK_SIZE, exception_on_overflow=False)
                frames.append(data)
            
            stream.stop_stream()
            stream.close()
            
            return b''.join(frames)
            
        except Exception as e:
            print(f"[Audio] Record error: {e}")
            return None
    
    async def wake_word_loop(self):
        """Listen for wake word and send audio to cloud when detected."""
        if not self.wake_word_detector:
            print("[Wake Word] Detector not initialized")
            return
        
        print("[Wake Word] 👂 Listening for wake words...")
        
        while self.running and self.ws:
            try:
                # Run wake word detection in thread to not block async loop
                def listen():
                    return self.wake_word_detector.listen_for_wake_word(timeout=5)
                
                # Listen for wake word (non-blocking with timeout)
                detected = await asyncio.get_event_loop().run_in_executor(None, listen)
                
                if detected and self.ws:
                    print("[Wake Word] ✅ Wake word detected! Recording query...")
                    
                    # Record full query
                    def record():
                        return self.wake_word_detector.record_query(config.QUERY_RECORD_DURATION)
                    
                    audio_bytes = await asyncio.get_event_loop().run_in_executor(None, record)
                    
                    if audio_bytes and self.ws:
                        print(f"[Wake Word] 📤 Sending {len(audio_bytes)} bytes to cloud...")
                        await self.send_message(
                            "audio_data",
                            audio_base64=base64.b64encode(audio_bytes).decode('utf-8'),
                            sample_rate=config.VAD_SAMPLE_RATE,
                            duration=config.QUERY_RECORD_DURATION
                        )
                        print("[Wake Word] ✅ Audio sent to cloud")
                
                # Small delay before next detection
                await asyncio.sleep(0.1)
                
            except websockets.exceptions.ConnectionClosed:
                print("[Wake Word] Connection lost")
                break
            except Exception as e:
                print(f"[Wake Word] Error: {e}")
                await asyncio.sleep(1)
    
    async def stream_loop(self):
        """Main loop for streaming video and sensor data to server."""
        print("[Stream] Starting...")
        
        image_interval = 1.0 / config.CAMERA_FPS
        sensor_interval = 5.0
        
        last_image_time = 0
        last_sensor_time = 0
        
        while self.running and self.ws:
            try:
                now = time.time()
                
                # Send image periodically
                if CAMERA_OK and self.camera and (now - last_image_time) >= image_interval:
                    image_bytes = self.capture_image()
                    if image_bytes:
                        self.last_image = image_bytes
                        await self.send_message(
                            "image_data",
                            image_base64=base64.b64encode(image_bytes).decode('utf-8'),
                            width=config.CAMERA_WIDTH,
                            height=config.CAMERA_HEIGHT
                        )
                    last_image_time = now
                
                # Send sensor data periodically
                if self.rover and (now - last_sensor_time) >= sensor_interval:
                    status = self.rover.get_status()
                    if status:
                        await self.send_message(
                            "sensor_data",
                            battery_voltage=status.get('voltage'),
                            battery_percent=self.rover.voltage_to_percent(status.get('voltage')),
                            temperature=status.get('temperature'),
                            imu_roll=status.get('roll'),
                            imu_pitch=status.get('pitch'),
                            imu_yaw=status.get('yaw')
                        )
                    last_sensor_time = now
                
                await asyncio.sleep(0.01)
                
            except websockets.exceptions.ConnectionClosed:
                print("[Stream] Connection lost")
                break
            except Exception as e:
                print(f"[Stream] Error: {e}")
                await asyncio.sleep(0.1)
    
    async def receive_loop(self):
        """Receive messages from server."""
        print("[Receive] Starting...")
        
        while self.running and self.ws:
            try:
                message = await asyncio.wait_for(self.ws.recv(), timeout=1.0)
                await self.handle_message(message)
            except asyncio.TimeoutError:
                continue
            except websockets.exceptions.ConnectionClosed:
                print("[Receive] Connection lost")
                break
            except Exception as e:
                print(f"[Receive] Error: {e}")
    
    async def run(self):
        """Main run loop."""
        self.running = True
        
        # Initialize hardware
        self.init_rover()
        self.init_camera()
        self.init_audio()
        
        # Initialize wake word detector (only once)
        if WAKE_WORD_OK:
            self.init_wake_word_detector()
        
        # Main loop with reconnection
        while self.running:
            if await self.connect_server():
                self.is_listening = True
                
                # Run stream, receive, and wake word loops
                tasks = [
                    asyncio.create_task(self.stream_loop()),
                    asyncio.create_task(self.receive_loop()),
                ]
                
                # Add wake word loop if available
                if self.wake_word_detector:
                    tasks.append(asyncio.create_task(self.wake_word_loop()))
                
                # Wait for any to finish (connection lost)
                done, pending = await asyncio.wait(
                    tasks,
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Cancel pending tasks
                for task in pending:
                    task.cancel()
                
                self.is_listening = False
                
                if self.ws:
                    await self.ws.close()
                    self.ws = None
                
                if self.running:
                    print("[Main] Reconnecting...")
                    await asyncio.sleep(config.RECONNECT_DELAY)
            else:
                break
        
        self.cleanup()
    
    def cleanup(self):
        """Clean up resources."""
        self.running = False
        
        if self.camera:
            self.camera.release()
        
        if self.wake_word_detector:
            self.wake_word_detector.cleanup()
        
        if hasattr(self, 'pyaudio') and self.pyaudio:
            self.pyaudio.terminate()
        
        if self.rover:
            self.rover.display_lines(["ROVY", "Disconnected", "", ""])
            self.rover.cleanup()
        
        print("[Client] Cleanup complete")
    
    def stop(self):
        """Stop the client."""
        print("[Client] Stopping...")
        self.running = False


# Signal handler for graceful shutdown
client = None

def signal_handler(sig, frame):
    print("\n[Signal] Shutting down...")
    if client:
        client.stop()
    sys.exit(0)


def main():
    global client
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    client = RovyClient()
    
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        client.stop()


if __name__ == "__main__":
    main()

