#!/bin/bash
# Setup Deepgram for wake word detection

echo "========================================="
echo "  Deepgram Wake Word Detector Setup"
echo "========================================="
echo ""

# Check if API key is provided
if [ -z "$1" ]; then
    echo "❌ Please provide your Deepgram API key"
    echo ""
    echo "Usage: $0 <DEEPGRAM_API_KEY>"
    echo ""
    echo "Get your API key from: https://console.deepgram.com/signup"
    echo "  1. Sign up for free account (includes $200 credit)"
    echo "  2. Go to API Keys section"
    echo "  3. Create a new API key"
    echo "  4. Run: $0 your_api_key_here"
    exit 1
fi

API_KEY="$1"

# Save API key to config
echo "DEEPGRAM_API_KEY=\"$API_KEY\"" >> /home/rovy/rovy_client/robot/.env

echo "✅ Deepgram API key saved to .env"
echo ""
echo "Testing Deepgram connection..."

# Test the connection
cd /home/rovy/rovy_client/robot
source venv/bin/activate

python3 -c "
import asyncio
import websockets

async def test():
    url = 'wss://api.deepgram.com/v1/listen?encoding=linear16&sample_rate=16000&channels=1'
    
    try:
        async with websockets.connect(url, additional_headers={'Authorization': 'Token $API_KEY'}) as ws:
            print('✅ Deepgram connection successful!')
            return True
    except Exception as e:
        print(f'❌ Connection failed: {e}')
        return False

result = asyncio.run(test())
exit(0 if result else 1)
"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Setup complete!"
    echo ""
    echo "Next steps:"
    echo "  1. The robot will now use Deepgram instead of local wake word detection"
    echo "  2. Restart the service: sudo systemctl restart rovy.service"
    echo ""
else
    echo ""
    echo "⚠️  Connection test failed. Please check:"
    echo "  - API key is correct"
    echo "  - Internet connection is working"
    echo "  - Deepgram service is accessible"
    echo ""
    exit 1
fi

