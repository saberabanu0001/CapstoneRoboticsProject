#!/bin/bash
# Install Deepgram SDK and dependencies for wake word detection

echo "========================================="
echo "  Deepgram SDK Installation"
echo "========================================="
echo ""

# Navigate to robot directory
cd /home/rovy/rovy_client/robot

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

echo ""
echo "Installing Deepgram SDK..."
echo "========================================="

# Install the latest Deepgram SDK v3.x
pip install --upgrade pip
pip install "deepgram-sdk>=3.0,<4.0"

# Install required dependencies
echo ""
echo "Installing dependencies..."
echo "========================================="
pip install pyaudio
pip install numpy scipy  # For audio resampling if needed

echo ""
echo "✅ Installation complete!"
echo ""
echo "Installed packages:"
pip show deepgram-sdk | grep -E "Name:|Version:"
echo ""

echo "========================================="
echo "  Next Steps"
echo "========================================="
echo ""
echo "1. Set your Deepgram API key in config.py or as environment variable:"
echo "   export DEEPGRAM_API_KEY='your_api_key_here'"
echo ""
echo "2. Get a free API key from: https://console.deepgram.com/signup"
echo "   - Sign up for free ($200 credit included)"
echo "   - Create an API key in the console"
echo ""
echo "3. Test the installation:"
echo "   python3 test_deepgram.py"
echo ""

