#!/usr/bin/env python3
"""
Test script for USB speaker configuration
Tests if the speaker device is correctly configured
"""
import subprocess
import sys
import os

# Add robot directory to path
sys.path.insert(0, os.path.dirname(__file__))
import config

def test_speaker_beep():
    """Test speaker with beep sound."""
    print(f"Testing speaker on device: {config.SPEAKER_DEVICE}")
    print("Generating beep sound...")
    
    # Generate a 3-second beep using ffmpeg
    result = subprocess.run(
        ['ffmpeg', '-f', 'lavfi', '-i', 'sine=frequency=1000:duration=3', 
         '-af', 'volume=1.0', '/tmp/test_beep.wav', '-y'],
        capture_output=True
    )
    
    if result.returncode != 0:
        print("❌ Failed to generate beep sound")
        return False
    
    print(f"Playing beep through {config.SPEAKER_DEVICE}...")
    result = subprocess.run(
        ['aplay', '-D', config.SPEAKER_DEVICE, '/tmp/test_beep.wav'],
        capture_output=True
    )
    
    if result.returncode == 0:
        print("✅ Speaker test successful!")
        return True
    else:
        print(f"❌ Speaker test failed: {result.stderr.decode()}")
        return False

def test_piper_tts():
    """Test Piper TTS with speaker."""
    import time
    print("\nWaiting 3 seconds for device to reset...")
    time.sleep(3)
    print("Testing Piper TTS...")
    
    piper_voice = config.PIPER_VOICES.get("en")
    if not os.path.exists(piper_voice):
        print(f"⚠️  Piper voice not found: {piper_voice}")
        return False
    
    # Generate speech
    result = subprocess.run(
        ['piper', '--model', piper_voice, '--output_file', '/tmp/test_tts.wav'],
        input="Testing speaker configuration with Piper text to speech.",
        text=True,
        capture_output=True,
        timeout=10
    )
    
    if result.returncode != 0:
        print(f"❌ Piper TTS failed: {result.stderr}")
        return False
    
    # Check if source file exists and has content
    if not os.path.exists('/tmp/test_tts.wav') or os.path.getsize('/tmp/test_tts.wav') == 0:
        print("❌ Source TTS file is missing or empty")
        return False
    
    print(f"✅ TTS file generated: {os.path.getsize('/tmp/test_tts.wav')} bytes")
    
    # Use ffmpeg to convert and pipe directly to aplay in one command
    # This avoids device state issues from multiple operations
    print(f"Playing TTS through {config.SPEAKER_DEVICE}...")
    
    # Single pipeline: ffmpeg converts and pipes to aplay
    cmd = f"ffmpeg -i /tmp/test_tts.wav -f wav -ac 2 -ar 48000 - 2>/dev/null | aplay -D {config.SPEAKER_DEVICE} -"
    
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        timeout=30
    )
    
    # Clean up temp file
    try:
        os.remove('/tmp/test_tts.wav')
    except:
        pass
    
    if result.returncode == 0:
        print("✅ Piper TTS test successful!")
        return True
    else:
        print(f"❌ TTS playback failed: {result.stderr}")
        return False

def check_volume():
    """Check speaker volume level."""
    print(f"\nChecking volume on card {config.SPEAKER_CARD}...")
    
    result = subprocess.run(
        ['amixer', '-c', str(config.SPEAKER_CARD), 'get', 'PCM'],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print(f"Volume status:\n{result.stdout}")
        return True
    else:
        print(f"⚠️  Could not get volume: {result.stderr}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("  USB Speaker Configuration Test")
    print("=" * 60)
    
    check_volume()
    test_piper_tts()
    
    print("\n" + "=" * 60)
    print("  Test Complete")
    print("=" * 60)

