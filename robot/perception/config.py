"""
Rovy Robot Client Configuration
Runs on Raspberry Pi, connects to cloud server via Tailscale
"""
import os

# =============================================================================
# Cloud Server Connection (via Tailscale)
# =============================================================================

# Your PC's Tailscale IP
PC_SERVER_IP = os.getenv("ROVY_PC_IP", "100.121.110.125")
WS_PORT = 8765
API_PORT = 8000  # Cloud server's HTTP API port

# WebSocket URL
SERVER_URL = f"ws://{PC_SERVER_IP}:{WS_PORT}"

# =============================================================================
# Robot Hardware
# =============================================================================

# Rover serial connection (ESP32)
# Pi5 uses /dev/ttyAMA0 for GPIO UART, older Pis may use /dev/ttyS0 or /dev/ttyACM0
ROVER_SERIAL_PORT = os.getenv("ROVY_SERIAL_PORT", "/dev/ttyAMA0")
ROVER_BAUDRATE = 115200

# =============================================================================
# Camera
# =============================================================================

CAMERA_INDEX = int(os.getenv("ROVY_CAMERA_INDEX", "1"))  # USB Camera is at /dev/video1
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 10  # Reduced from 15 to lower USB bandwidth for audio stability
JPEG_QUALITY = 70  # Reduced for lower bandwidth

# =============================================================================
# Audio (ReSpeaker)
# =============================================================================

SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 1024
AUDIO_BUFFER_SECONDS = 2.0

# =============================================================================
# Wake Word Detection (Local on Pi)
# =============================================================================

# Wake words to listen for (case-insensitive)
WAKE_WORDS = ["hey rovy", "hey robbie", "hey rolly", "hey", "rovy", "robbie", "rolly"]

# Deepgram API for wake word detection (more reliable than local)
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "1d0af4b59c6353a2940618aa858ec0bdfe80bda7")
USE_DEEPGRAM = True  # Set to True to use Deepgram (cloud-based, accurate), False for local detector

# VAD (Voice Activity Detection) settings
VAD_SAMPLE_RATE = 16000
VAD_THRESHOLD = 0.3  # Confidence threshold for speech detection (0.0-1.0) - higher = less sensitive to noise
VAD_MIN_SPEECH_DURATION = 1.0  # Minimum speech duration in seconds (wait for complete phrases)
VAD_MIN_SILENCE_DURATION = 1.2  # Minimum silence after speech in seconds (ensure sentence ends)

# Whisper settings for local wake word detection
WHISPER_MODEL = "tiny"  # tiny, base, small (tiny is fastest for Pi)
WHISPER_DEVICE = "cpu"  # Use CPU on Pi
WHISPER_COMPUTE_TYPE = "int8"  # int8 for CPU efficiency

# Audio recording after wake word detected
QUERY_RECORD_DURATION = 3.0  # Record 3 seconds after wake word for full query (shorter = more responsive)
QUERY_TIMEOUT = 10.0  # Max time to wait for query after wake word

# USB Microphone settings (card 4, device 0 - USB Headphone Set microphone)
USB_MIC_SAMPLE_RATE = 44100  # Native sample rate of USB mic (will resample to 16kHz for VAD/Whisper)
USB_MIC_DEVICE = "plughw:4,0"  # ALSA device for microphone input

# =============================================================================
# Audio Output (Speaker)
# =============================================================================

# USB Speaker device for audio playback (HK-5008)
# Card 2 - UACDemoV1.0 (Jieli Technology)
SPEAKER_DEVICE = "plughw:2,0"  # ALSA device for speaker
SPEAKER_CARD = 2  # Card number for amixer volume control
SPEAKER_DEFAULT_VOLUME = 80  # Default volume % (80% prevents clipping at high volumes)

# =============================================================================
# Text-to-Speech (Piper)
# =============================================================================

# Piper TTS voice model paths for different languages
# Download voices from: https://github.com/rhasspy/piper/blob/master/VOICES.md
PIPER_VOICES = {
    "en": "/home/rovy/rovy_client/models/piper/en_US-hfc_male-medium.onnx",
    "es": "/home/rovy/rovy_client/models/piper/es_ES-davefx-medium.onnx",
    "fr": "/home/rovy/rovy_client/models/piper/fr_FR-siwis-medium.onnx",
    "de": "/home/rovy/rovy_client/models/piper/de_DE-thorsten-medium.onnx",
    "it": "/home/rovy/rovy_client/models/piper/it_IT-riccardo-x_low.onnx",
    "pt": "/home/rovy/rovy_client/models/piper/pt_BR-faber-medium.onnx",
    "ru": "/home/rovy/rovy_client/models/piper/ru_RU-dmitri-medium.onnx",
    "zh": "/home/rovy/rovy_client/models/piper/zh_CN-huayan-medium.onnx",
    "vi": "/home/rovy/rovy_client/models/piper/vi_VN-vais1000-medium.onnx",
    "hi": "/home/rovy/rovy_client/models/piper/hi_IN-pratham-medium.onnx",
    "ne": "/home/rovy/rovy_client/models/piper/ne_NP-chitwan-medium.onnx",
    "fa": "/home/rovy/rovy_client/models/piper/fa_IR-amir-medium.onnx",
    # Korean (ko) is not available in Piper TTS
}

# Default voice (backward compatibility)
PIPER_VOICE = PIPER_VOICES.get("en")

# =============================================================================
# Connection
# =============================================================================

RECONNECT_DELAY = 5
MAX_RECONNECT_ATTEMPTS = 0  # 0 = infinite
