#!/usr/bin/env python3
"""
Example: Using Deepgram Wake Word Detector
Demonstrates how to use the corrected Deepgram wake word detection
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from wake_word_detector_deepgram import DeepgramWakeWordDetector
    import config
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nMake sure you've installed the Deepgram SDK:")
    print("  ./install_deepgram.sh")
    sys.exit(1)


async def main():
    """Example usage of DeepgramWakeWordDetector"""
    
    # Get API key
    api_key = config.DEEPGRAM_API_KEY
    if not api_key or api_key == "":
        print("❌ No API key found in config.py")
        print("\nPlease set DEEPGRAM_API_KEY in config.py")
        print("Get a free key from: https://console.deepgram.com/signup")
        return
    
    print("="*60)
    print("  Deepgram Wake Word Detector Example")
    print("="*60)
    print("")
    print("Wake words: hey rovy, rovy, hey robot, hey")
    print("The detector uses fuzzy matching for common misheard variations")
    print("")
    print("Press Ctrl+C to stop")
    print("")
    
    # Initialize detector
    detector = DeepgramWakeWordDetector(
        api_key=api_key,
        wake_words=config.WAKE_WORDS,
        sample_rate=16000,
        device_sample_rate=44100,  # USB mic native rate
        device_index=None  # Auto-detect microphone
    )
    
    # Callback when wake word is detected
    def on_wake_word(transcript):
        print(f"\n🎉 WAKE WORD DETECTED!")
        print(f"   Transcript: '{transcript}'")
        print("")
    
    try:
        # Listen for wake word (with 30 second timeout for testing)
        print("👂 Listening... (say 'hey rovy' or any wake word)")
        print("")
        
        detected = await detector.listen_for_wake_word_async(
            callback=on_wake_word,
            timeout=30.0  # 30 seconds
        )
        
        if detected:
            print("\n✅ Wake word was detected successfully!")
            print(f"   Last transcript: '{detector.last_transcript}'")
        else:
            print("\n⏱️  Timeout - no wake word detected")
            print("   Try saying 'hey rovy' or another wake word")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up
        print("\nCleaning up...")
        detector.cleanup()
        print("✅ Done!")


if __name__ == "__main__":
    asyncio.run(main())

