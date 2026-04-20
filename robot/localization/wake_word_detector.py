#!/usr/bin/env python3
"""
Wake Word Detector using Silero VAD + Whisper Tiny
Efficiently detects "Hey Rovy" locally on Raspberry Pi
"""
import time
import logging
from typing import Optional, Callable
import numpy as np

# Try to import dependencies with helpful error messages
try:
    import pyaudio
    PYAUDIO_OK = True
except ImportError:
    PYAUDIO_OK = False
    print("ERROR: PyAudio not installed. Run: pip install pyaudio")

try:
    import torch
    torch.set_num_threads(4)  # Optimize for Pi 5
    TORCH_OK = True
except ImportError:
    TORCH_OK = False
    print("ERROR: torch not installed. Run: pip install torch")

try:
    from faster_whisper import WhisperModel
    WHISPER_OK = True
except ImportError:
    WHISPER_OK = False
    print("ERROR: faster-whisper not installed. Run: pip install faster-whisper")

logger = logging.getLogger(__name__)


class WakeWordDetector:
    """
    Efficient wake word detector using:
    1. Silero VAD - Detects when someone is speaking (low CPU)
    2. Whisper tiny - Transcribes speech to check for wake word
    """
    
    def __init__(
        self,
        wake_words: list = None,
        sample_rate: int = 16000,
        device_sample_rate: int = None,
        device_index: Optional[int] = None,
        vad_threshold: float = 0.5,
        whisper_model: str = "tiny",
        whisper_device: str = "cpu",
        whisper_compute_type: str = "int8",
        min_speech_duration: float = 0.25,
        min_silence_duration: float = 0.5,
    ):
        """
        Initialize wake word detector.
        
        Args:
            wake_words: List of wake words to detect (case-insensitive)
            sample_rate: Processing sample rate for VAD/Whisper (16000 recommended)
            device_sample_rate: Device native sample rate (e.g., 44100). If None, uses sample_rate
            device_index: Audio device index (None = default/auto-detect)
            vad_threshold: VAD confidence threshold (0.0-1.0)
            whisper_model: Whisper model size (tiny, base, small)
            whisper_device: Device for Whisper (cpu, cuda)
            whisper_compute_type: Compute type (int8, float16, float32)
            min_speech_duration: Minimum speech duration in seconds
            min_silence_duration: Minimum silence duration after speech
        """
        if not PYAUDIO_OK:
            raise RuntimeError("PyAudio not available. Install: pip install pyaudio")
        if not TORCH_OK:
            raise RuntimeError("Torch not available. Install: pip install torch")
        if not WHISPER_OK:
            raise RuntimeError("faster-whisper not available. Install: pip install faster-whisper")
        
        self.wake_words = [w.lower().strip() for w in (wake_words or ["hey rovy"])]
        self.sample_rate = sample_rate  # Processing rate (16kHz for VAD/Whisper)
        self.device_sample_rate = device_sample_rate or sample_rate  # Device native rate
        self.needs_resampling = (self.device_sample_rate != self.sample_rate)
        self.device_index = device_index
        self.vad_threshold = vad_threshold
        self.min_speech_duration = min_speech_duration
        self.min_silence_duration = min_silence_duration
        
        logger.info(f"Initializing WakeWordDetector for: {self.wake_words}")
        if self.needs_resampling:
            logger.info(f"Audio: {self.device_sample_rate}Hz (device) -> {self.sample_rate}Hz (processing)")
        else:
            logger.info(f"Audio: {self.sample_rate}Hz")
        
        # Initialize PyAudio
        self.pyaudio = pyaudio.PyAudio()
        
        # Find microphone device if not specified
        if self.device_index is None:
            self.device_index = self._find_microphone()
        
        logger.info(f"Using audio device index: {self.device_index}")
        
        # Load Silero VAD
        logger.info("Loading Silero VAD model...")
        try:
            # Try to load from local cache first, fallback to download
            import silero_vad
            # Use the installed package's model directly
            self.vad_model = silero_vad.load_silero_vad()
            # Get utilities from the package
            self.get_speech_timestamps = silero_vad.get_speech_timestamps
            self.read_audio = silero_vad.read_audio
            logger.info("✅ Silero VAD loaded from package")
        except Exception as e:
            logger.error(f"Failed to load Silero VAD from package, trying torch.hub: {e}")
            try:
                self.vad_model, utils = torch.hub.load(
                    repo_or_dir='snakers4/silero-vad',
                    model='silero_vad',
                    force_reload=False,
                    onnx=False,
                    skip_validation=True  # Skip validation to avoid GitHub API calls
                )
                (self.get_speech_timestamps, _, self.read_audio, *_) = utils
                logger.info("✅ Silero VAD loaded from torch.hub")
            except Exception as e2:
                logger.error(f"Failed to load Silero VAD: {e2}")
                raise
        
        # Load Whisper model
        logger.info(f"Loading Whisper {whisper_model} model...")
        try:
            self.whisper_model = WhisperModel(
                whisper_model,
                device=whisper_device,
                compute_type=whisper_compute_type,
                cpu_threads=4,  # Optimize for Pi 5
                num_workers=1
            )
            logger.info(f"✅ Whisper {whisper_model} loaded")
        except Exception as e:
            logger.error(f"Failed to load Whisper: {e}")
            raise
        
        self.stream = None
        self.running = False
        
    def _find_microphone(self) -> Optional[int]:
        """Find USB microphone or any input audio device."""
        for i in range(self.pyaudio.get_device_count()):
            info = self.pyaudio.get_device_info_by_index(i)
            name = info.get('name', '').lower()
            max_input_channels = info.get('maxInputChannels', 0)
            
            # Look for USB microphones (prioritize non-camera devices)
            if max_input_channels > 0:
                if 'camera' not in name:  # Skip camera microphones
                    logger.info(f"Found microphone: {info['name']} (device {i})")
                    return i
        
        logger.warning("No microphone found, using default device")
        return None
    
    def _detect_speech(self, audio_chunk: np.ndarray) -> bool:
        """
        Use Silero VAD to detect if audio contains speech.
        
        Args:
            audio_chunk: Audio data as numpy array (16-bit int) at device sample rate
        
        Returns:
            True if speech detected, False otherwise
        """
        try:
            # Resample if needed
            if self.needs_resampling:
                # Simple decimation for downsampling
                decimation_factor = int(self.device_sample_rate / self.sample_rate)
                audio_chunk = audio_chunk[::decimation_factor]
            
            # Validate chunk size for Silero VAD - it requires EXACT sample counts
            # At 16kHz: exactly 512 samples; at 8kHz: exactly 256 samples
            if self.sample_rate == 16000:
                required_samples = 512
            elif self.sample_rate == 8000:
                required_samples = 256
            else:
                required_samples = 512
            
            if len(audio_chunk) != required_samples:
                logger.warning(f"Audio chunk size mismatch: {len(audio_chunk)} != {required_samples} samples (expected for {self.sample_rate}Hz)")
                # Try to pad or truncate to required size
                if len(audio_chunk) < required_samples:
                    # Pad with zeros
                    audio_chunk = np.pad(audio_chunk, (0, required_samples - len(audio_chunk)), mode='constant')
                else:
                    # Truncate
                    audio_chunk = audio_chunk[:required_samples]
            
            # Convert to float32 tensor normalized to [-1, 1]
            audio_float = audio_chunk.astype(np.float32) / 32768.0
            audio_tensor = torch.from_numpy(audio_float)
            
            # Get speech probability
            speech_prob = self.vad_model(audio_tensor, self.sample_rate).item()
            
            return speech_prob >= self.vad_threshold
            
        except Exception as e:
            logger.error(f"VAD error: {e}")
            return False
    
    def _transcribe_audio(self, audio_data: np.ndarray) -> Optional[str]:
        """
        Transcribe audio using Whisper.
        
        Args:
            audio_data: Audio as numpy array (16-bit int) at device sample rate
        
        Returns:
            Transcribed text or None
        """
        try:
            # Resample if needed
            if self.needs_resampling:
                # Simple decimation for downsampling
                decimation_factor = int(self.device_sample_rate / self.sample_rate)
                audio_data = audio_data[::decimation_factor]
            
            # Convert to float32 normalized to [-1, 1]
            audio_float = audio_data.astype(np.float32) / 32768.0
            
            # Transcribe
            segments, info = self.whisper_model.transcribe(
                audio_float,
                language="en",  # Can be None for auto-detect
                beam_size=1,  # Faster inference
                vad_filter=False,  # We already did VAD
                without_timestamps=True
            )
            
            # Combine all segments
            text = " ".join([seg.text for seg in segments]).strip()
            
            return text if text else None
            
        except Exception as e:
            logger.error(f"Whisper error: {e}")
            return None
    
    def _check_wake_word(self, text: str) -> bool:
        """Check if transcribed text contains wake word."""
        if not text:
            return False
        
        text_lower = text.lower().strip()
        
        for wake_word in self.wake_words:
            if wake_word in text_lower:
                return True
        
        return False
    
    def listen_for_wake_word(
        self,
        callback: Optional[Callable[[str], None]] = None,
        timeout: Optional[float] = None
    ) -> bool:
        """
        Listen continuously for wake word.
        
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
            # Calculate chunk size - Silero VAD has STRICT requirements:
            # At 16kHz: EXACTLY 512 samples
            # At 8kHz: EXACTLY 256 samples
            # Calculate required samples for processing rate
            if self.sample_rate == 16000:
                required_samples_after_resample = 512
            elif self.sample_rate == 8000:
                required_samples_after_resample = 256
            else:
                # Default fallback
                required_samples_after_resample = 512
            
            if self.needs_resampling:
                decimation_factor = int(self.device_sample_rate / self.sample_rate)
                chunk_samples = required_samples_after_resample * decimation_factor
            else:
                chunk_samples = required_samples_after_resample
            
            # Open audio stream at device's native sample rate
            self.stream = self.pyaudio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.device_sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=chunk_samples
            )
            
            # Buffer for collecting speech
            speech_buffer = []
            is_speaking = False
            silence_start = None
            speech_start = None
            
            while self.running:
                # Check timeout
                if timeout and (time.time() - start_time) > timeout:
                    logger.info("⏱️ Wake word detection timeout")
                    return False
                
                try:
                    # Read audio chunk
                    audio_bytes = self.stream.read(chunk_samples, exception_on_overflow=False)
                    audio_chunk = np.frombuffer(audio_bytes, dtype=np.int16)
                    
                    # Detect speech with VAD
                    has_speech = self._detect_speech(audio_chunk)
                    
                    if has_speech:
                        # Speech detected
                        if not is_speaking:
                            # Start of speech
                            is_speaking = True
                            speech_start = time.time()
                            speech_buffer = []
                            logger.info("🗣️ Speech started")
                        
                        # Add to buffer
                        speech_buffer.append(audio_chunk)
                        silence_start = None
                        
                    else:
                        # No speech detected
                        if is_speaking:
                            # Possible end of speech
                            if silence_start is None:
                                silence_start = time.time()
                            
                            # Check if silence long enough
                            silence_duration = time.time() - silence_start
                            
                            if silence_duration >= self.min_silence_duration:
                                # End of speech - process it
                                speech_duration = time.time() - speech_start
                                
                                if speech_duration >= self.min_speech_duration:
                                    logger.info(f"🎤 Processing speech ({speech_duration:.2f}s)")
                                    
                                    # Transcribe the speech
                                    audio_data = np.concatenate(speech_buffer)
                                    text = self._transcribe_audio(audio_data)
                                    
                                    if text:
                                        logger.info(f"📝 Heard: '{text}'")
                                        
                                        # Check for wake word
                                        if self._check_wake_word(text):
                                            logger.info(f"✅ Wake word detected!")
                                            
                                            if callback:
                                                callback(text)
                                            
                                            return True
                                
                                # Reset
                                is_speaking = False
                                speech_buffer = []
                                silence_start = None
                                speech_start = None
                
                except Exception as e:
                    logger.error(f"Error processing audio: {e}")
                    time.sleep(0.1)
        
        except KeyboardInterrupt:
            logger.info("Wake word detection interrupted")
            return False
        
        finally:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
    
    def record_query(self, duration: float) -> bytes:
        """
        Record audio for specified duration (after wake word detected).
        
        Args:
            duration: Recording duration in seconds
        
        Returns:
            Raw audio bytes (16-bit PCM)
        """
        logger.info(f"🎙️ Recording query for {duration}s...")
        
        try:
            if not self.stream:
                self.stream = self.pyaudio.open(
                    format=pyaudio.paInt16,
                    channels=1,
                    rate=self.device_sample_rate,
                    input=True,
                    input_device_index=self.device_index,
                    frames_per_buffer=1024
                )
            
            frames = []
            num_chunks = int(self.device_sample_rate / 1024 * duration)
            
            for _ in range(num_chunks):
                data = self.stream.read(1024, exception_on_overflow=False)
                frames.append(data)
            
            audio_bytes = b''.join(frames)
            logger.info(f"✅ Recorded {len(audio_bytes)} bytes")
            
            return audio_bytes
            
        except Exception as e:
            logger.error(f"Recording error: {e}")
            return b''
    
    def stop(self):
        """Stop wake word detection."""
        logger.info("Stopping wake word detector...")
        self.running = False
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
    
    def cleanup(self):
        """Clean up resources."""
        self.stop()
        
        if hasattr(self, 'pyaudio') and self.pyaudio:
            self.pyaudio.terminate()
        
        logger.info("Wake word detector cleaned up")


if __name__ == "__main__":
    # Test the wake word detector
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    detector = WakeWordDetector(
        wake_words=["hey rovy", "rovy"],
        sample_rate=16000,
        device_sample_rate=48000  # USB mic's native rate
    )
    
    try:
        print("\n🎤 Say 'Hey Rovy' to test...")
        print("Press Ctrl+C to exit\n")
        
        while True:
            detected = detector.listen_for_wake_word(timeout=30)
            
            if detected:
                print("\n✅ Wake word detected! Recording query...")
                audio = detector.record_query(5.0)
                print(f"✅ Recorded {len(audio)} bytes\n")
            else:
                print("No wake word detected, listening again...")
    
    except KeyboardInterrupt:
        print("\n\nExiting...")
    
    finally:
        detector.cleanup()

