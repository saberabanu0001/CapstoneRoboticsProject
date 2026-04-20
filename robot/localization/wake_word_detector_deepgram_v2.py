#!/usr/bin/env python3
"""
Deepgram SDK-based Wake Word Detector (Official Implementation)
Uses Deepgram's official Python SDK for reliable streaming transcription.
"""
import asyncio
import time
import logging
from typing import Optional, Callable

try:
    import pyaudio
    PYAUDIO_OK = True
except ImportError:
    PYAUDIO_OK = False

try:
    from deepgram import (
        DeepgramClient,
        DeepgramClientOptions,
        LiveTranscriptionEvents,
        LiveOptions,
    )
    DEEPGRAM_SDK_OK = True
except ImportError:
    DEEPGRAM_SDK_OK = False

logger = logging.getLogger(__name__)


class DeepgramWakeWordDetector:
    """
    Wake word detector using Deepgram's official SDK.
    Much more reliable than manual WebSocket implementation.
    """
    
    def __init__(
        self,
        api_key: str,
        wake_words: list = None,
        sample_rate: int = 16000,
        device_sample_rate: Optional[int] = None,
        device_index: Optional[int] = None,
    ):
        """Initialize Deepgram-based wake word detector."""
        if not PYAUDIO_OK:
            raise RuntimeError("PyAudio not available")
        if not DEEPGRAM_SDK_OK:
            raise RuntimeError("Deepgram SDK not available - install with: pip install deepgram-sdk")
        
        self.api_key = api_key
        self.wake_words = [w.lower().strip() for w in (wake_words or ["hey rovy"])]
        self.sample_rate = sample_rate
        self.device_sample_rate = device_sample_rate or sample_rate
        self.device_index = device_index
        self.needs_resampling = (self.device_sample_rate != self.sample_rate)
        
        print(f"[Deepgram] Initializing with official SDK for wake words: {self.wake_words}")
        print(f"[Deepgram] Device rate: {self.device_sample_rate}Hz -> Deepgram rate: {sample_rate}Hz")
        
        # Initialize PyAudio
        self.pyaudio = pyaudio.PyAudio()
        
        # Find microphone
        if self.device_index is None:
            self.device_index = self._find_microphone()
        
        self.stream = None
        self.dg_connection = None
        self.running = False
        self.wake_word_detected = False
        self.last_transcript = ""
        
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
        wake_word_variants = [
            # Rovvy variants
            "roevee", "rovee", "romy", "ruby", "rovie", "rovi", "rovey",
            "rov me", "rove", "rope", "roby", "robi", "robey",
            # Robbie variants  
            "roby", "robby", "rabi", "rabbi", "robey", "robbey",
            # Rolly variants
            "rollie", "rolie", "roly", "rowley", "rawley", "rolley"
        ]
        
        for variant in wake_word_variants:
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
        Listen for wake word using Deepgram's official SDK.
        
        Args:
            callback: Function to call when wake word detected
            timeout: Maximum time to listen (None = forever)
        
        Returns:
            True if wake word detected, False if timeout
        """
        print(f"[Deepgram] 👂 Listening for: {self.wake_words}")
        
        self.running = True
        self.wake_word_detected = False
        start_time = time.time()
        
        try:
            # Initialize Deepgram client
            config = DeepgramClientOptions(
                options={"keepalive": "true"}
            )
            deepgram = DeepgramClient(self.api_key, config)
            
            # Create connection (using asyncwebsocket - asynclive is deprecated)
            self.dg_connection = deepgram.listen.asyncwebsocket.v("1")
            
            # Configure transcription options
            options = LiveOptions(
                model="nova-2",
                language="en-US",
                encoding="linear16",
                sample_rate=self.sample_rate,
                channels=1,
                punctuate=True,
                smart_format=True,
                interim_results=True,
                utterance_end_ms="1000",  # 1 second of silence ends utterance
                vad_events=True,
                endpointing=1000,  # 1000ms of silence to finalize
            )
            
            # Set up event handlers (must be async and accept connection as first param)
            async def on_message(connection, result, **kwargs):
                try:
                    sentence = result.channel.alternatives[0].transcript
                    
                    if len(sentence) == 0:
                        return
                    
                    is_final = result.is_final
                    
                    print(f"[Deepgram] {'📝 FINAL' if is_final else '💭 interim'}: '{sentence}'")
                    
                    # Check for wake word on final transcripts (access outer self via closure)
                    if is_final and self._check_wake_word(sentence):
                        print(f"[Deepgram] ✅ Wake word detected!")
                        self.wake_word_detected = True
                        self.last_transcript = sentence
                        self.running = False
                        if callback:
                            callback(sentence)
                
                except Exception as e:
                    print(f"[Deepgram] Error in on_message: {e}")
                    import traceback
                    traceback.print_exc()
            
            async def on_error(connection, error, **kwargs):
                print(f"[Deepgram] ❌ Error: {error}")
            
            async def on_close(connection, *args, **kwargs):
                print(f"[Deepgram] Connection closed")
                self.running = False
            
            # Register event handlers
            self.dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
            self.dg_connection.on(LiveTranscriptionEvents.Error, on_error)
            self.dg_connection.on(LiveTranscriptionEvents.Close, on_close)
            
            # Start connection
            if not await self.dg_connection.start(options):
                print("[Deepgram] Failed to start connection")
                return False
            
            print(f"[Deepgram] ✅ Connected to Deepgram streaming API (SDK v5)")
            
            # Open audio stream
            chunk_size = int(self.device_sample_rate * 0.1)  # 100ms chunks
            
            self.stream = self.pyaudio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.device_sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=chunk_size
            )
            print(f"[Deepgram] ✅ Audio stream opened at {self.device_sample_rate}Hz")
            
            # Stream audio to Deepgram
            chunks_sent = 0
            while self.running:
                # Check timeout
                if timeout and (time.time() - start_time) > timeout:
                    print(f"[Deepgram] Timeout after {timeout}s")
                    break
                
                # Read audio
                try:
                    audio_bytes = await asyncio.wait_for(
                        asyncio.to_thread(
                            self.stream.read,
                            chunk_size,
                            exception_on_overflow=False
                        ),
                        timeout=2.0
                    )
                    
                    # Resample if needed
                    if self.needs_resampling:
                        import numpy as np
                        from scipy import signal
                        
                        audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                        num_samples = int(len(audio_np) * self.sample_rate / self.device_sample_rate)
                        audio_resampled = signal.resample(audio_np, num_samples)
                        audio_bytes = (audio_resampled * 32768.0).astype(np.int16).tobytes()
                    
                    # Send to Deepgram (must await)
                    await self.dg_connection.send(audio_bytes)
                    chunks_sent += 1
                    
                    # Check if wake word was detected
                    if self.wake_word_detected:
                        break
                    
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    print(f"[Deepgram] Audio read error: {e}")
                    break
            
            # Clean up
            await self.dg_connection.finish()
            
            return self.wake_word_detected
        
        except Exception as e:
            print(f"[Deepgram] Error: {e}")
            import traceback
            traceback.print_exc()
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

