#!/bin/bash
# Installation script for Wake Word Detection on Raspberry Pi
# Installs Silero VAD + Whisper tiny for local wake word detection

set -e  # Exit on error

echo "=========================================="
echo "  Installing Wake Word Detection"
echo "  (Silero VAD + Whisper tiny)"
echo "=========================================="
echo ""

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo "⚠️  WARNING: This doesn't appear to be a Raspberry Pi"
    echo "   Continuing anyway..."
    echo ""
fi

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Python $PYTHON_VERSION found"
echo ""

# Check if running in virtual environment (recommended)
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  WARNING: Not running in a virtual environment"
    echo "   It's recommended to use a virtual environment"
    read -p "   Continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Exiting. Create a venv with: python3 -m venv venv && source venv/bin/activate"
        exit 1
    fi
fi

# Update pip
echo "Updating pip..."
python3 -m pip install --upgrade pip
echo ""

# Install PyTorch (CPU version for Pi)
echo "Installing PyTorch (CPU version)..."
echo "This may take a while on Raspberry Pi..."
python3 -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
echo "✅ PyTorch installed"
echo ""

# Install Silero VAD dependencies
echo "Installing Silero VAD..."
python3 -m pip install silero-vad
echo "✅ Silero VAD installed"
echo ""

# Install faster-whisper (optimized Whisper for CPU)
echo "Installing faster-whisper..."
python3 -m pip install faster-whisper
echo "✅ faster-whisper installed"
echo ""

# Install other dependencies from requirements.txt
if [ -f "requirements.txt" ]; then
    echo "Installing remaining dependencies from requirements.txt..."
    python3 -m pip install -r requirements.txt
    echo "✅ All dependencies installed"
else
    echo "⚠️  requirements.txt not found, skipping"
fi
echo ""

# Download Whisper tiny model (first run)
echo "Downloading Whisper tiny model..."
echo "This will happen automatically on first run, but we can pre-download it:"
python3 -c "from faster_whisper import WhisperModel; print('Downloading...'); WhisperModel('tiny', device='cpu', compute_type='int8'); print('✅ Model downloaded')"
echo ""

# Test wake word detector
echo "Testing wake word detector..."
if python3 -c "from wake_word_detector import WakeWordDetector" 2>/dev/null; then
    echo "✅ Wake word detector module loads successfully!"
else
    echo "❌ ERROR: Wake word detector failed to load"
    echo "   Check the error messages above"
    exit 1
fi
echo ""

echo "=========================================="
echo "  ✅ Installation Complete!"
echo "=========================================="
echo ""
echo "Wake word detection is ready to use!"
echo ""
echo "To test it, run:"
echo "  python3 wake_word_detector.py"
echo ""
echo "To start the robot client with wake word detection:"
echo "  python3 main.py"
echo ""
echo "Or restart the systemd service:"
echo "  sudo systemctl restart rovy"
echo ""
echo "Default wake words: hey rovy, rovy, hey robot"
echo "Edit config.py to change wake words"
echo ""

