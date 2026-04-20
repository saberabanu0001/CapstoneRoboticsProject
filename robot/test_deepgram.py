#!/usr/bin/env python3
"""
Test script for Deepgram SDK wake word detector
Tests the installation and basic functionality
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from deepgram import DeepgramClient, DeepgramClientOptions, LiveTranscriptionEvents, LiveOptions
    print("✅ Deepgram SDK imported successfully")
except ImportError as e:
    print(f"❌ Failed to import Deepgram SDK: {e}")
    print("\nPlease install the SDK:")
    print("  pip install deepgram-sdk")
    sys.exit(1)

try:
    import pyaudio
    print("✅ PyAudio imported successfully")
except ImportError as e:
    print(f"❌ Failed to import PyAudio: {e}")
    print("\nPlease install PyAudio:")
    print("  pip install pyaudio")
    sys.exit(1)

# Import config
try:
    import config
    API_KEY = config.DEEPGRAM_API_KEY
    print(f"✅ API key loaded from config: {API_KEY[:10]}...")
except Exception as e:
    print(f"⚠️  Could not load API key from config: {e}")
    API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
    if API_KEY:
        print(f"✅ API key loaded from environment: {API_KEY[:10]}...")
    else:
        print("❌ No API key found!")
        print("\nPlease set your API key in one of these ways:")
        print("  1. Set in config.py: DEEPGRAM_API_KEY = 'your_key_here'")
        print("  2. Set as environment variable: export DEEPGRAM_API_KEY='your_key_here'")
        print("\nGet a free key from: https://console.deepgram.com/signup")
        sys.exit(1)

print("\n" + "="*50)
print("  Testing Deepgram Connection")
print("="*50 + "\n")


async def test_connection():
    """Test basic connection to Deepgram API"""
    try:
        # Initialize client
        deepgram = DeepgramClient(API_KEY)
        print("✅ DeepgramClient initialized")
        
        # Create a live connection (using asyncwebsocket - asynclive is deprecated)
        dg_connection = deepgram.listen.asyncwebsocket.v("1")
        print("✅ Live connection object created")
        
        # Configure options
        options = LiveOptions(
            model="nova-2",
            language="en-US",
            encoding="linear16",
            sample_rate=16000,
            channels=1,
        )
        
        # Start connection (this will test if API key and connection work)
        print("\nAttempting to connect to Deepgram API...")
        start_result = await dg_connection.start(options)
        
        if start_result:
            print("✅ Connection started successfully!")
            
            # Give it a moment to fully establish
            await asyncio.sleep(1)
            
            # Close connection
            await dg_connection.finish()
            print("✅ Connection closed cleanly")
            
            return True
        else:
            print("❌ Failed to start connection")
            return False
            
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_microphone():
    """Test microphone availability"""
    print("\n" + "="*50)
    print("  Testing Microphone")
    print("="*50 + "\n")
    
    try:
        p = pyaudio.PyAudio()
        
        print("Available audio input devices:")
        found_mic = False
        for i in range(p.get_device_count()):
            info = p.get_device_info_by_index(i)
            if info.get('maxInputChannels', 0) > 0:
                print(f"  [{i}] {info['name']}")
                print(f"      Max Channels: {info['maxInputChannels']}")
                print(f"      Default Sample Rate: {int(info['defaultSampleRate'])}Hz")
                found_mic = True
        
        if found_mic:
            print("\n✅ Microphone(s) detected")
        else:
            print("\n⚠️  No microphone detected")
        
        p.terminate()
        return found_mic
        
    except Exception as e:
        print(f"❌ Microphone test failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("Starting Deepgram tests...\n")
    
    # Test connection
    conn_ok = await test_connection()
    
    # Test microphone
    mic_ok = await test_microphone()
    
    # Summary
    print("\n" + "="*50)
    print("  Test Summary")
    print("="*50)
    print(f"Deepgram Connection: {'✅ PASS' if conn_ok else '❌ FAIL'}")
    print(f"Microphone:          {'✅ PASS' if mic_ok else '⚠️  WARN'}")
    
    if conn_ok and mic_ok:
        print("\n🎉 All tests passed! You're ready to use Deepgram wake word detection.")
        print("\nTo use it in your robot:")
        print("  1. Make sure USE_DEEPGRAM = True in config.py")
        print("  2. Restart the robot service")
        return 0
    elif conn_ok:
        print("\n⚠️  Deepgram connection works, but no microphone detected.")
        print("Please check your microphone connection.")
        return 1
    else:
        print("\n❌ Tests failed. Please check:")
        print("  - API key is correct")
        print("  - Internet connection is working")
        print("  - Deepgram SDK is installed correctly")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

