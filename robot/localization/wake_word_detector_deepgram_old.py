#!/usr/bin/env python3
"""
Deepgram-based Wake Word Detector
Uses Deepgram's streaming API for real-time transcription and wake word detection.
No local VAD needed - Deepgram handles everything.
"""
import asyncio
import json
import time
import logging
from typing import Optional, Callable

try:
    import pyaudio
    PYAUDIO_OK = True
except ImportError:
    PYAUDIO_OK = False

try:
    import websockets
    WEBSOCKETS_OK = True
except ImportError:
    WEBSOCKETS_OK = False

logger = logging.getLogger(__name__)


class DeepgramWakeWordDetector:
    """
    Wake word detector using Deepgram's streaming API.
    Benefits:
    - No local VAD processing (Deepgram handles it)
    - Better transcription quality
    - Built-in silence detection
    - Lower latency
    """
    
    def __init__(
        self,
        api_key: str,
        wake_words: list = None,
        sample_rate: int = 16000,
        device_sample_rate: Optional[int] = None,
        device_index: Optional[int] = None,
    ):
        """
        Initialize Deepgram-based wake word detector.
        
        Args:
            api_key: Deepgram API key
            wake_words: List of wake words to detect (case-insensitive)
            sample_rate: Target sample rate for Deepgram (16000 recommended)
            device_sample_rate: Device's native sample rate (if different, will resample)
            device_index: Audio device index (None = default)
        """
        if not PYAUDIO_OK:
            raise RuntimeError("PyAudio not available")
        if not WEBSOCKETS_OK:
            raise RuntimeError("websockets not available")
        
        self.api_key = api_key
        self.wake_words = [w.lower().strip() for w in (wake_words or ["hey rovy"])]
        self.sample_rate = sample_rate
        self.device_sample_rate = device_sample_rate or sample_rate
        self.device_index = device_index
        self.needs_resampling = (self.device_sample_rate != self.sample_rate)
        
        # Deepgram WebSocket URL
        self.deepgram_url = (
            f"wss://api.deepgram.com/v1/listen"
            f"?encoding=linear16"
            f"&sample_rate={sample_rate}"
            f"&channels=1"
            f"&endpointing=true"  # Automatic utterance end detection
            f"&interim_results=false"  # Only final results
            f"&punctuate=true"
            f"&smart_format=true"
        )
        
        print(f"[Deepgram] Initializing for wake words: {self.wake_words}")
        print(f"[Deepgram] Device rate: {self.device_sample_rate}Hz -> Deepgram rate: {sample_rate}Hz")
        if self.needs_resampling:
            print(f"[Deepgram] Will resample audio from {self.device_sample_rate}Hz to {sample_rate}Hz")
        
        # Initialize PyAudio
        self.pyaudio = pyaudio.PyAudio()
        
        # Find microphone
        if self.device_index is None:
            self.device_index = self._find_microphone()
        
        self.stream = None
        self.ws = None
        self.running = False
        self.wake_word_callback = None
        
    def _find_microphone(self) -> Optional[int]:
        """Find audio input device."""
        for i in range(self.pyaudio.get_device_count()):
            info = self.pyaudio.get_device_info_by_index(i)
            if info.get('maxInputChannels', 0) > 0:
                print(f"[Deepgram] Found microphone: {info['name']} (index {i})")
                return i
        print("[Deepgram] No microphone found, using default")
        return None
    
    def _check_wake_word(self, text: str) -> bool:
        """Check if transcribed text contains wake word."""
        if not text:
            return False
        
        text_lower = text.lower().strip()
        
        for wake_word in self.wake_words:
            if wake_word in text_lower:
                return True
        
        # Fuzzy matching for common misheard variations
        rovy_variants = [
            "roevee", "rovee", "romy", "ruby", "rovie", "robbie",
            "roby", "robi", "rovey", "robey", "rovi", "rovvy"
        ]
        
        for variant in rovy_variants:
            if variant in text_lower:
                print(f"[Deepgram] Fuzzy match: '{text}' matched variant '{variant}'")
                return True
        
        return False
    
    async def listen_for_wake_word_async(
        self,
        callback: Optional[Callable[[str], None]] = None,
        timeout: Optional[float] = None
    ) -> bool:
        """
        Listen for wake word using Deepgram streaming.
        
        Args:
            callback: Function to call when wake word detected
            timeout: Maximum time to listen (None = forever)
        
        Returns:
            True if wake word detected, False if timeout
        """
        print(f"[Deepgram] 👂 Listening for: {self.wake_words}")
        
        self.running = True
        self.wake_word_callback = callback
        start_time = time.time()
        
        try:
            # Open audio stream with device sample rate
            chunk_size = int(self.device_sample_rate * 0.1)  # 100ms chunks at device rate
            
            self.stream = self.pyaudio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.device_sample_rate,  # Use device rate for capture
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=chunk_size
            )
            print(f"[Deepgram] ✅ Audio stream opened at {self.device_sample_rate}Hz ({chunk_size} samples per chunk)")
            
            # Connect to Deepgram with auth header
            async with websockets.connect(
                self.deepgram_url,
                additional_headers={"Authorization": f"Token {self.api_key}"}
            ) as ws:
                self.ws = ws
                print(f"[Deepgram] ✅ Connected to Deepgram streaming API")
                
                # Create tasks for sending and receiving
                send_task = asyncio.create_task(self._send_audio())
                receive_task = asyncio.create_task(self._receive_transcripts())
                
                # Wait for either wake word detection or timeout
                done, pending = await asyncio.wait(
                    [send_task, receive_task],
                    timeout=timeout,
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Cancel remaining tasks
                for task in pending:
                    task.cancel()
                
                # Check if wake word was detected
                for task in done:
                    if task.result():
                        return True
                
                return False
        
        except Exception as e:
            print(f"[Deepgram] Error: {e}")
            return False
        
        finally:
            self.running = False
            if self.stream:
                try:
                    if self.stream.is_active():
                        self.stream.stop_stream()
                    self.stream.close()
                except:
                    pass
                self.stream = None
    
    async def _send_audio(self):
        """Send audio chunks to Deepgram."""
        chunks_sent = 0
        try:
            print("[Deepgram] Starting audio send loop...")
            while self.running and self.stream and self.ws:
                # Read audio (non-blocking with timeout)
                try:
                    audio_bytes = await asyncio.wait_for(
                        asyncio.to_thread(
                            self.stream.read,
                            int(self.device_sample_rate * 0.1),  # 100ms at device rate
                            exception_on_overflow=False
                        ),
                        timeout=2.0
                    )
                    
                    # Resample if needed
                    if self.needs_resampling:
                        import numpy as np
                        from scipy import signal
                        
                        # Convert to float
                        audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                        
                        # Resample
                        num_samples = int(len(audio_np) * self.sample_rate / self.device_sample_rate)
                        audio_resampled = signal.resample(audio_np, num_samples)
                        
                        # Convert back to int16
                        audio_bytes = (audio_resampled * 32768.0).astype(np.int16).tobytes()
                    
                    # Send raw PCM audio to Deepgram
                    await self.ws.send(audio_bytes)
                    chunks_sent += 1
                    
                    # Log every 50 chunks (5 seconds)
                    if chunks_sent % 50 == 0:
                        print(f"[Deepgram] Sent {chunks_sent} audio chunks ({chunks_sent * 0.1:.1f}s of audio)")
                    
                except asyncio.TimeoutError:
                    # Silently continue - this is normal for continuous streaming
                    continue
                except Exception as e:
                    print(f"[Deepgram] Send error: {e}")
                    break
            
            # Send close message
            if self.ws:
                try:
                    await self.ws.send(json.dumps({"type": "CloseStream"}))
                except:
                    pass
            
        except Exception as e:
            print(f"[Deepgram] Send loop error: {e}")
        
        return False
    
    async def _receive_transcripts(self):
        """Receive and process transcripts from Deepgram."""
        messages_received = 0
        try:
            print("[Deepgram] Starting receive loop...")
            while self.running and self.ws:
                try:
                    message = await asyncio.wait_for(self.ws.recv(), timeout=1.0)
                    messages_received += 1
                    
                    data = json.loads(message)
                    
                    # Log all message types for debugging
                    msg_type = data.get("type", "unknown")
                    if messages_received <= 3 or msg_type != "Metadata":
                        print(f"[Deepgram] Received message #{messages_received}: type={msg_type}")
                    
                    # Check for transcript
                    if data.get("type") == "Results":
                        channel = data.get("channel", {})
                        alternatives = channel.get("alternatives", [])
                        
                        print(f"[Deepgram] DEBUG: channel keys={list(channel.keys())}, alternatives={len(alternatives)}")
                        
                        if alternatives:
                            transcript = alternatives[0].get("transcript", "")
                            confidence = alternatives[0].get("confidence", 0)
                            is_final = channel.get("is_final", False)
                            
                            print(f"[Deepgram] Transcript='{transcript}', is_final={is_final}, confidence={confidence:.3f}")
                            
                            if is_final and transcript:
                                print(f"[Deepgram] 📝 Heard: '{transcript}'")
                                
                                # Check for wake word
                                if self._check_wake_word(transcript):
                                    print(f"[Deepgram] ✅ Wake word detected!")
                                    self.running = False
                                    
                                    if self.wake_word_callback:
                                        self.wake_word_callback(transcript)
                                    
                                    return True
                    
                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    print("[Deepgram] Connection closed")
                    break
                except Exception as e:
                    print(f"[Deepgram] Receive error: {e}")
                    break
        
        except Exception as e:
            print(f"[Deepgram] Receive loop error: {e}")
        
        return False
    
    def stop(self):
        """Stop wake word detection."""
        print("[Deepgram] Stopping...")
        self.running = False
    
    def cleanup(self):
        """Clean up resources."""
        self.stop()
        
        if self.stream:
            try:
                if self.stream.is_active():
                    self.stream.stop_stream()
                self.stream.close()
            except:
                pass
            self.stream = None
        
        if hasattr(self, 'pyaudio') and self.pyaudio:
            try:
                self.pyaudio.terminate()
                self.pyaudio = None
            except:
                pass
        
        print("[Deepgram] ✅ Cleaned up")


if __name__ == "__main__":
    # Test the Deepgram wake word detector
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python wake_word_detector_deepgram.py <DEEPGRAM_API_KEY>")
        sys.exit(1)
    
    api_key = sys.argv[1]
    
    detector = DeepgramWakeWordDetector(
        api_key=api_key,
        wake_words=["hey rovy", "rovy", "hey"],
        sample_rate=48000  # Use native device rate
    )
    
    async def test():
        print("\n🎤 Say 'Hey Rovy' to test...")
        print("Press Ctrl+C to exit\n")
        
        try:
            while True:
                detected = await detector.listen_for_wake_word_async(timeout=30)
                
                if detected:
                    print("\n✅ Wake word detected!\n")
                    # Restart listening
                else:
                    print("No wake word in last 30s, listening again...")
        
        except KeyboardInterrupt:
            print("\n\nExiting...")
        finally:
            detector.cleanup()
    
    asyncio.run(test())

