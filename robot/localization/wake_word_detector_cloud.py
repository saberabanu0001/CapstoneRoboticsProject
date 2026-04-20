#!/usr/bin/env python3
"""
Cloud-based Wake Word Detector
Uses local VAD + cloud Whisper for accurate, fast transcription
"""
import time
import logging
import asyncio
import json
import base64
from typing import Optional, Callable
import numpy as np

try:
    import pyaudio
    PYAUDIO_OK = True
except ImportError:
    PYAUDIO_OK = False

try:
    import torch
    torch.set_num_threads(4)
    TORCH_OK = True
except ImportError:
    TORCH_OK = False

try:
    import aiohttp
    AIOHTTP_OK = True
except ImportError:
    AIOHTTP_OK = False

logger = logging.getLogger(__name__)


class CloudWakeWordDetector:
    """
    Efficient wake word detector:
    1. Local Silero VAD - Detects speech (fast, low CPU)
    2. Cloud Whisper - Transcribes speech (accurate, fast on GPU)
    """
    
    def __init__(
        self,
        wake_words: list = None,
        cloud_url: str = "ws://100.121.110.125:8000/voice",
        sample_rate: int = 16000,
        device_sample_rate: int = None,
        device_index: Optional[int] = None,
        vad_threshold: float = 0.3,
        min_speech_duration: float = 0.25,
        min_silence_duration: float = 0.5,
    ):
        """
        Initialize cloud-based wake word detector.
        
        Args:
            wake_words: List of wake words to detect (case-insensitive)
            cloud_url: WebSocket URL for cloud transcription service
            sample_rate: Processing sample rate for VAD (16000 recommended)
            device_sample_rate: Device native sample rate (e.g., 48000)
            device_index: Audio device index (None = default/auto-detect)
            vad_threshold: VAD confidence threshold (0.0-1.0)
            min_speech_duration: Minimum speech duration in seconds
            min_silence_duration: Minimum silence duration after speech
        """
        if not PYAUDIO_OK:
            raise RuntimeError("PyAudio not available")
        if not TORCH_OK:
            raise RuntimeError("Torch not available")
        if not AIOHTTP_OK:
            raise RuntimeError("aiohttp not available - install: pip install aiohttp")
        
        self.wake_words = [w.lower().strip() for w in (wake_words or ["hey rovy"])]
        self.cloud_url = cloud_url
        self.sample_rate = sample_rate
        self.device_sample_rate = device_sample_rate or sample_rate
        self.needs_resampling = (self.device_sample_rate != self.sample_rate)
        self.device_index = device_index
        self.vad_threshold = vad_threshold
        self.min_speech_duration = min_speech_duration
        self.min_silence_duration = min_silence_duration
        
        # AGC (Automatic Gain Control) for distant speech
        self.target_rms = 0.15  # Target RMS level for normalization (increased for better distant voice pickup)
        
        print(f"[WakeWord] Initializing for: {self.wake_words}")
        print(f"[WakeWord] VAD Settings: threshold={self.vad_threshold}, min_speech={self.min_speech_duration}s, min_silence={self.min_silence_duration}s")
        if self.needs_resampling:
            logger.info(f"Audio: {self.device_sample_rate}Hz (device) -> {self.sample_rate}Hz (processing)")
        
        # Initialize PyAudio
        self.pyaudio = pyaudio.PyAudio()
        
        # Find microphone
        if self.device_index is None:
            self.device_index = self._find_microphone()
        
        # Load Silero VAD only (no local Whisper!)
        logger.info("Loading Silero VAD model...")
        try:
            import silero_vad
            self.vad_model = silero_vad.load_silero_vad()
            logger.info("✅ Silero VAD loaded")
        except Exception as e:
            logger.error(f"Failed to load Silero VAD: {e}")
            raise
        
        self.stream = None
        self.running = False
        
    def _find_microphone(self) -> Optional[int]:
        """Find USB microphone or any input audio device."""
        for i in range(self.pyaudio.get_device_count()):
            info = self.pyaudio.get_device_info_by_index(i)
            name = info.get('name', '').lower()
            max_input_channels = info.get('maxInputChannels', 0)
            
            if max_input_channels > 0 and 'camera' not in name:
                logger.info(f"Found microphone: {info['name']} (device {i})")
                return i
        
        logger.warning("No microphone found, using default device")
        return None
    
    def _detect_speech(self, audio_chunk: np.ndarray) -> bool:
        """Use Silero VAD to detect if audio contains speech."""
        try:
            # Convert to float
            audio_float = audio_chunk.astype(np.float32) / 32768.0
            
            # Apply AGC (Automatic Gain Control) to boost quiet audio from distance
            rms = np.sqrt(np.mean(audio_float ** 2))
            if rms > 0.0005:  # Lower threshold to boost quieter sounds
                gain = self.target_rms / rms
                # Limit gain to prevent excessive noise amplification
                gain = min(gain, 15.0)  # Max 15x boost for distant speech
                audio_float = audio_float * gain
                # Clip to prevent distortion
                audio_float = np.clip(audio_float, -1.0, 1.0)
            
            # Resample if needed using high-quality resampling
            if self.needs_resampling:
                from scipy import signal
                # Target exactly 512 samples for VAD
                audio_float = signal.resample(audio_float, 512)
            
            # Ensure exactly 512 samples for 16kHz
            if len(audio_float) != 512:
                if len(audio_float) < 512:
                    audio_float = np.pad(audio_float, (0, 512 - len(audio_float)))
                else:
                    audio_float = audio_float[:512]
            
            # Convert to tensor
            audio_tensor = torch.from_numpy(audio_float)
            
            # Get speech probability
            speech_prob = self.vad_model(audio_tensor, self.sample_rate).item()
            
            return speech_prob >= self.vad_threshold
            
        except Exception as e:
            logger.error(f"VAD error: {e}")
            return False
    
    async def _transcribe_cloud(self, audio_data: np.ndarray) -> Optional[str]:
        """Send audio to cloud for transcription using REST API."""
        try:
            # audio_data is already int16 from the buffer
            # Convert to float for processing
            audio_float = audio_data.astype(np.float32) / 32768.0
            
            # Resample if needed using high-quality resampling
            if self.needs_resampling:
                from scipy import signal
                # Calculate the number of samples after resampling
                num_samples = int(len(audio_float) * self.sample_rate / self.device_sample_rate)
                # Use scipy's resample for better quality
                audio_float = signal.resample(audio_float, num_samples)
            
            # Apply AGC to boost quiet audio from distance (reduced to preserve quality)
            rms = np.sqrt(np.mean(audio_float ** 2))
            if rms > 0.005:  # Only amplify reasonable audio to avoid noise amplification
                gain = self.target_rms / rms
                gain = min(gain, 3.0)  # Max 3x boost to preserve audio quality
                audio_float = audio_float * gain
                print(f"[WakeWord] Applied AGC to wake detection: gain={gain:.2f}x")
            
            # Final normalization to optimal range
            if len(audio_float) > 0:
                max_val = np.abs(audio_float).max()
                if max_val > 0:
                    audio_float = audio_float / max_val * 0.95  # Normalize to 95% to avoid clipping
            
            # Convert back to int16
            audio_int16 = (audio_float * 32767).astype(np.int16)
            
            print(f"[WakeWord] Prepared audio: {len(audio_int16)} samples at {self.sample_rate}Hz")
            
            # Create proper WAV file in memory
            import io
            import wave
            
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(audio_int16.tobytes())
            
            wav_bytes = wav_buffer.getvalue()
            print(f"[WakeWord] Created WAV file: {len(wav_bytes)} bytes, sending to {self.cloud_url.replace('ws://', 'http://').replace('/voice', '')}/stt")
            
            # DEBUG: Optionally save audio to file for inspection (disabled by default)
            # debug_filename = f"/tmp/debug_audio_{int(time.time())}.wav"
            # with open(debug_filename, 'wb') as f:
            #     f.write(wav_bytes)
            # logger.debug(f"🔍 Saved audio to {debug_filename}")
            
            # Use REST API /stt endpoint
            base_url = self.cloud_url.replace("ws://", "http://").replace("/voice", "")
            stt_url = f"{base_url}/stt"
            
            # Send via HTTP POST
            async with aiohttp.ClientSession() as session:
                # Create form data with WAV file
                data = aiohttp.FormData()
                data.add_field('audio',
                              wav_bytes,
                              filename='audio.wav',
                              content_type='audio/wav')
                
                async with session.post(stt_url, data=data, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        result = await response.json()
                        text = result.get("text", "")
                        if text:
                            return text.strip()
                        else:
                            return None
                    else:
                        error_text = await response.text()
                        logger.warning(f"Cloud transcription failed with status {response.status}: {error_text}")
                        return None
            
        except Exception as e:
            logger.error(f"Cloud transcription error: {e}")
            return None
    
    def _check_wake_word(self, text: str) -> bool:
        """Check if transcribed text contains wake word with fuzzy matching."""
        if not text:
            return False
        
        text_lower = text.lower().strip()
        
        # Exact match first
        for wake_word in self.wake_words:
            if wake_word in text_lower:
                return True
        
        # Fuzzy match for common misheard variations
        # "Rovy" sounds like: roevee, romy, ruby, rovie, robbie, etc.
        rovy_variants = [
            "roevee", "rovee", "romy", "ruby", "rovie", "robbie", 
            "roby", "robi", "rovey", "robey", "rovi", "rovvy"
        ]
        
        for variant in rovy_variants:
            if variant in text_lower:
                logger.info(f"✨ Fuzzy match: '{text}' matched variant '{variant}'")
                return True
        
        # Check if "hey" appears with any word starting with 'ro'
        if "hey" in text_lower:
            words = text_lower.split()
            for word in words:
                if word.startswith("ro") and len(word) >= 3:
                    logger.info(f"✨ Fuzzy match: 'hey' + word starting with 'ro': '{word}'")
                    return True
        
        return False
    
    async def listen_for_wake_word_async(
        self,
        callback: Optional[Callable[[str], None]] = None,
        timeout: Optional[float] = None
    ) -> bool:
        """
        Listen continuously for wake word (async version).
        
        Args:
            callback: Function to call when wake word detected
            timeout: Maximum time to listen (None = forever)
        
        Returns:
            True if wake word detected, False if timeout
        """
        logger.info(f"👂 Listening for wake words: {self.wake_words}")
        
        self.running = True
        start_time = time.time()
        
        try:
            # Calculate chunk size for VAD
            required_samples_after_resample = 512  # VAD requires exactly 512 samples
            if self.needs_resampling:
                decimation_factor = int(self.device_sample_rate / self.sample_rate)
                chunk_samples = required_samples_after_resample * decimation_factor
            else:
                chunk_samples = required_samples_after_resample
            
            # Ensure any previous stream is closed before opening new one
            if self.stream:
                try:
                    if self.stream.is_active():
                        self.stream.stop_stream()
                    self.stream.close()
                except:
                    pass
                self.stream = None
            
            # Wait for ALSA to fully release device
            await asyncio.sleep(0.5)
            
            # Open audio stream with retry logic and longer delays
            max_retries = 5
            for retry in range(max_retries):
                try:
                    self.stream = self.pyaudio.open(
                        format=pyaudio.paInt16,
                        channels=1,
                        rate=self.device_sample_rate,
                        input=True,
                        input_device_index=self.device_index,
                        frames_per_buffer=chunk_samples
                    )
                    logger.info(f"✅ Audio stream opened successfully")
                    break  # Success
                except Exception as e:
                    logger.error(f"Failed to open audio stream (attempt {retry+1}/{max_retries}): {e}")
                    if retry < max_retries - 1:
                        # Exponential backoff: wait longer each retry
                        wait_time = min(2.0 ** retry, 8.0)  # 1s, 2s, 4s, 8s, 8s
                        logger.info(f"Waiting {wait_time}s before retry...")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error("❌ Could not open audio stream after retries")
                        return False
            
            # Buffer for collecting speech
            speech_buffer = []
            pre_speech_buffer = []  # Buffer to capture audio BEFORE speech starts
            max_pre_speech_chunks = 5  # Keep last 5 chunks before speech
            is_speaking = False
            silence_start = None
            speech_start = None
            
            while self.running:
                # Check timeout
                if timeout and (time.time() - start_time) > timeout:
                    logger.info("⏱️ Wake word detection timeout")
                    return False
                
                # Read audio chunk (non-blocking with timeout protection)
                try:
                    # Simple check - if no stream, we're done (detection cycle ended)
                    if not self.stream:
                        logger.info("Stream closed, ending detection cycle")
                        break
                    
                    # Check if stream is still valid before reading
                    if not self.stream.is_active():
                        logger.warning("Stream is no longer active, ending detection cycle")
                        break
                    
                    # Wrap blocking read in asyncio.to_thread with timeout to prevent hanging
                    try:
                        audio_bytes = await asyncio.wait_for(
                            asyncio.to_thread(self.stream.read, chunk_samples, exception_on_overflow=False),
                            timeout=1.5  # Reasonable timeout for USB audio read
                        )
                    except asyncio.TimeoutError:
                        logger.error("⚠️ Audio read timeout - device may be busy or stream corrupted")
                        # Force cleanup of corrupted stream immediately
                        try:
                            if self.stream:
                                if self.stream.is_active():
                                    self.stream.stop_stream()
                                self.stream.close()
                                self.stream = None
                        except Exception as cleanup_err:
                            logger.error(f"Error during stream cleanup: {cleanup_err}")
                        # Raise exception to trigger failure counter and PyAudio reinitialization
                        raise RuntimeError("Audio stream timeout - ALSA stream corrupted, needs reinitialization")
                    except IOError as io_error:
                        logger.error(f"⚠️ Audio I/O error (ALSA buffer issue): {io_error}")
                        # Force cleanup
                        try:
                            if self.stream:
                                if self.stream.is_active():
                                    self.stream.stop_stream()
                                self.stream.close()
                                self.stream = None
                        except:
                            pass
                        # Raise to trigger reinitialization
                        raise RuntimeError(f"Audio I/O error - ALSA needs reinitialization: {io_error}")
                    except Exception as read_error:
                        logger.error(f"⚠️ Audio read error: {read_error}")
                        # Force cleanup of corrupted stream
                        try:
                            if self.stream:
                                if self.stream.is_active():
                                    self.stream.stop_stream()
                                self.stream.close()
                                self.stream = None
                        except:
                            pass
                        # Re-raise to trigger failure counter
                        raise
                    
                    audio_chunk = np.frombuffer(audio_bytes, dtype=np.int16)
                    
                    # Detect speech with VAD
                    has_speech = self._detect_speech(audio_chunk)
                    
                    if has_speech:
                        # Speech detected
                        if not is_speaking:
                            # Start of speech - include pre-speech context
                            is_speaking = True
                            speech_start = time.time()
                            # Start with pre-speech buffer for context
                            speech_buffer = list(pre_speech_buffer)
                            print(f"[WakeWord] 🗣️ Speech started")
                            logger.info("🗣️ Speech started")
                        
                        speech_buffer.append(audio_chunk)
                        silence_start = None
                        # Clear pre-speech buffer while speaking
                        pre_speech_buffer = []
                        
                    else:
                        # No speech
                        if not is_speaking:
                            # Keep rolling buffer of audio before speech starts
                            pre_speech_buffer.append(audio_chunk)
                            if len(pre_speech_buffer) > max_pre_speech_chunks:
                                pre_speech_buffer.pop(0)
                        
                        if is_speaking:
                            if silence_start is None:
                                silence_start = time.time()
                            
                            silence_duration = time.time() - silence_start
                            
                            if silence_duration >= self.min_silence_duration:
                                # End of speech - transcribe via cloud
                                speech_duration = time.time() - speech_start
                                print(f"[WakeWord] Speech ended: duration={speech_duration:.2f}s, required={self.min_speech_duration}s")
                                
                                if speech_duration >= self.min_speech_duration:
                                    print(f"[WakeWord] ✅ Duration OK, processing {speech_duration:.2f}s via cloud...")
                                    logger.info(f"🎤 Processing speech ({speech_duration:.2f}s) via cloud...")
                                    
                                    # Transcribe via cloud with timeout protection
                                    try:
                                        audio_data = np.concatenate(speech_buffer)
                                        text = await asyncio.wait_for(
                                            self._transcribe_cloud(audio_data),
                                            timeout=10.0  # Max 10s for transcription
                                        )
                                        
                                        if text:
                                            logger.info(f"📝 Heard: '{text}'")
                                            
                                            # Check for wake word
                                            if self._check_wake_word(text):
                                                logger.info(f"✅ Wake word detected!")
                                                
                                                if callback:
                                                    callback(text)
                                                
                                                return True
                                    except asyncio.TimeoutError:
                                        logger.warning("Cloud transcription timeout")
                                    except Exception as trans_error:
                                        logger.error(f"Transcription error: {trans_error}")
                                
                                # Reset
                                is_speaking = False
                                speech_buffer = []
                                silence_start = None
                                speech_start = None
                
                except Exception as e:
                    logger.error(f"Error processing audio: {e}")
                    await asyncio.sleep(0.1)
                
                # Small delay to prevent CPU spinning
                await asyncio.sleep(0.01)
        
        except KeyboardInterrupt:
            logger.info("Wake word detection interrupted")
            return False
        
        finally:
            self.running = False
            if self.stream:
                try:
                    # Only stop if stream is active to avoid errors
                    if self.stream.is_active():
                        self.stream.stop_stream()
                except Exception as e:
                    logger.warning(f"Error stopping stream during cleanup: {e}")
                
                try:
                    # Always try to close, even if stop failed
                    self.stream.close()
                except Exception as e:
                    logger.warning(f"Error closing stream during cleanup: {e}")
                
                # Clear reference to allow garbage collection
                self.stream = None
                
                logger.info("Wake word detection stream cleaned up")
    
    def stop(self):
        """Stop wake word detection."""
        logger.info("Stopping wake word detector...")
        self.running = False
        
        if self.stream:
            try:
                self.stream.stop_stream()
            except:
                pass
            try:
                self.stream.close()
            except:
                pass
            self.stream = None
    
    def pause(self):
        """Pause wake word detection temporarily (e.g., during speech/music)."""
        # DISABLED: Pause/resume operations cause ALSA memory corruption
        # Just set a flag and let the detection loop handle it
        logger.debug("Wake word detector pause requested (no-op to avoid ALSA corruption)")
        pass
    
    def resume(self):
        """Resume wake word detection after pause."""
        # DISABLED: Pause/resume operations cause ALSA memory corruption  
        # Just set a flag and let the detection loop handle it
        logger.debug("Wake word detector resume requested (no-op to avoid ALSA corruption)")
        pass
    
    def cleanup(self):
        """Clean up resources."""
        self.stop()
        
        # Force garbage collection before terminating PyAudio
        import gc
        gc.collect()
        
        if hasattr(self, 'pyaudio') and self.pyaudio:
            try:
                self.pyaudio.terminate()
                self.pyaudio = None
                logger.info("✅ PyAudio terminated")
            except Exception as e:
                logger.error(f"Error terminating PyAudio: {e}")
        
        logger.info("✅ Wake word detector cleaned up")


# Synchronous wrapper for backward compatibility
def run_async_listener(detector, timeout=None):
    """Run async listener in event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            detector.listen_for_wake_word_async(timeout=timeout)
        )
    finally:
        loop.close()


if __name__ == "__main__":
    # Test the cloud wake word detector
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    detector = CloudWakeWordDetector(
        wake_words=["hey rovy", "rovy", "hey"],
        sample_rate=16000,
        device_sample_rate=48000,
        vad_threshold=0.25,  # Lower threshold for distance detection
        min_speech_duration=0.5,  # Capture more context
        min_silence_duration=0.7  # Wait longer to ensure sentence ends
    )
    
    try:
        print("\n🎤 Say 'Hey Rovy' to test (using cloud transcription)...")
        print("Press Ctrl+C to exit\n")
        
        while True:
            detected = run_async_listener(detector, timeout=30)
            
            if detected:
                print("\n✅ Wake word detected!\n")
            else:
                print("No wake word detected, listening again...")
    
    except KeyboardInterrupt:
        print("\n\nExiting...")
    
    finally:
        detector.cleanup()

