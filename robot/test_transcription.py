#!/usr/bin/env python3
"""
Real-time Transcription Test
Test how well Deepgram transcribes your speech
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions
    import pyaudio
    import config
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nMake sure you've installed the Deepgram SDK:")
    print("  ./install_deepgram.sh")
    sys.exit(1)


class TranscriptionTester:
    """Test real-time transcription quality"""
    
    def __init__(self, api_key: str, device_sample_rate: int = 44100, device_index: int = None):
        self.api_key = api_key
        self.sample_rate = 16000
        self.device_sample_rate = device_sample_rate
        self.pyaudio = pyaudio.PyAudio()
        self.device_index = device_index if device_index is not None else self._find_microphone()
        self.stream = None
        self.dg_connection = None
        self.running = False
    
    def _find_microphone(self):
        """Find audio input device and update sample rate."""
        device_count = self.pyaudio.get_device_count()
        print(f"\nℹ️  Scanning {device_count} audio devices...")
        
        for i in range(device_count):
            try:
                info = self.pyaudio.get_device_info_by_index(i)
                max_input = info.get('maxInputChannels', 0)
                
                # Debug: print all devices
                print(f"   Device {i}: {info.get('name', 'Unknown')} - Input channels: {max_input}")
                
                if max_input > 0:
                    # Get the device's native sample rate
                    native_rate = int(info.get('defaultSampleRate', 44100))
                    print(f"\n✅ Using microphone: {info['name']} (index {i})")
                    print(f"   Native sample rate: {native_rate}Hz\n")
                    # Update device sample rate to match what device supports
                    self.device_sample_rate = native_rate
                    return i
            except Exception as e:
                print(f"   Error checking device {i}: {e}")
                continue
        
        print("\n⚠️  No microphone found with input channels")
        print("   Attempting to use default device...\n")
        return None
        
    async def test_transcription(self, duration: float = 30.0):
        """Test transcription for a specified duration"""
        
        print("="*70)
        print("  DEEPGRAM TRANSCRIPTION TEST")
        print("="*70)
        print(f"\nDuration: {duration} seconds")
        print("Model: nova-2 (latest, most accurate)")
        print("\nStart speaking clearly...")
        print("Both interim (💭) and final (📝) results will be shown")
        print("\nPress Ctrl+C to stop early\n")
        print("-"*70)
        
        self.running = True
        
        try:
            # Initialize Deepgram client
            deepgram = DeepgramClient(self.api_key)
            
            # Create connection
            self.dg_connection = deepgram.listen.asyncwebsocket.v("1")
            
            # Track transcription quality metrics
            interim_count = 0
            final_count = 0
            total_words = 0
            
            # Event handlers (must be async and accept connection as first param)
            async def on_message(connection, result, **kwargs):
                nonlocal interim_count, final_count, total_words
                
                try:
                    sentence = result.channel.alternatives[0].transcript
                    
                    if len(sentence) == 0:
                        return
                    
                    is_final = result.is_final
                    confidence = result.channel.alternatives[0].confidence if hasattr(result.channel.alternatives[0], 'confidence') else None
                    
                    if is_final:
                        final_count += 1
                        words = sentence.split()
                        total_words += len(words)
                        
                        # Show final results with confidence
                        if confidence:
                            print(f"📝 FINAL (confidence: {confidence:.2%}): {sentence}")
                        else:
                            print(f"📝 FINAL: {sentence}")
                    else:
                        interim_count += 1
                        # Show interim results (these update in real-time)
                        print(f"💭 interim: {sentence}")
                
                except Exception as e:
                    print(f"❌ Error in on_message: {e}")
            
            async def on_error(connection, error, **kwargs):
                print(f"\n❌ Error: {error}")
                self.running = False
            
            async def on_close(connection, close_msg, **kwargs):
                print(f"\nℹ️  Connection closed")
                self.running = False
            
            async def on_metadata(connection, metadata, **kwargs):
                print(f"ℹ️  Metadata received")
            
            # Register event handlers
            self.dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
            self.dg_connection.on(LiveTranscriptionEvents.Error, on_error)
            self.dg_connection.on(LiveTranscriptionEvents.Close, on_close)
            self.dg_connection.on(LiveTranscriptionEvents.Metadata, on_metadata)
            
            # Configure options
            options = LiveOptions(
                model="nova-2",  # Latest, most accurate model
                language="en-US",
                encoding="linear16",
                sample_rate=self.sample_rate,
                channels=1,
                punctuate=True,
                smart_format=True,
                interim_results=True,
                utterance_end_ms="1000",
                vad_events=True,
                endpointing=1000,
            )
            
            # Start connection
            if not await self.dg_connection.start(options):
                print("❌ Failed to start connection")
                return False
            
            print("✅ Connected to Deepgram\n")
            
            # Open audio stream
            # Try to open with detected rate, fallback to common rates if it fails
            rates_to_try = [self.device_sample_rate, 16000, 48000, 44100, 8000]
            
            for rate in rates_to_try:
                try:
                    chunk_size = int(rate * 0.1)  # 100ms chunks
                    
                    self.stream = self.pyaudio.open(
                        format=pyaudio.paInt16,
                        channels=1,
                        rate=rate,
                        input=True,
                        input_device_index=self.device_index,
                        frames_per_buffer=chunk_size
                    )
                    
                    # Success! Update the actual rate being used
                    if rate != self.device_sample_rate:
                        print(f"ℹ️  Device rate {self.device_sample_rate}Hz not supported, using {rate}Hz")
                    self.device_sample_rate = rate
                    break
                    
                except OSError as e:
                    if rate == rates_to_try[-1]:
                        # Last attempt failed
                        raise
                    # Try next rate
                    continue
            
            # Stream audio
            start_time = asyncio.get_event_loop().time()
            
            while self.running:
                # Check timeout
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > duration:
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
                    if self.device_sample_rate != self.sample_rate:
                        import numpy as np
                        from scipy import signal
                        
                        audio_np = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32768.0
                        num_samples = int(len(audio_np) * self.sample_rate / self.device_sample_rate)
                        audio_resampled = signal.resample(audio_np, num_samples)
                        audio_bytes = (audio_resampled * 32768.0).astype(np.int16).tobytes()
                    
                    # Send to Deepgram (must await)
                    await self.dg_connection.send(audio_bytes)
                    
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    print(f"❌ Audio error: {e}")
                    break
            
            # Clean up
            await self.dg_connection.finish()
            
            # Show stats
            print("\n" + "="*70)
            print("  TRANSCRIPTION STATISTICS")
            print("="*70)
            print(f"Duration: {elapsed:.1f}s")
            print(f"Interim results: {interim_count}")
            print(f"Final results: {final_count}")
            print(f"Total words transcribed: {total_words}")
            if elapsed > 0:
                print(f"Words per minute: {total_words / (elapsed / 60):.1f}")
            print("\n✅ Test complete!")
            
            return True
        
        except KeyboardInterrupt:
            print("\n\n⚠️  Stopped by user")
            return False
        
        except Exception as e:
            print(f"\n❌ Error: {e}")
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
            if self.pyaudio:
                try:
                    self.pyaudio.terminate()
                except:
                    pass
    
    def cleanup(self):
        """Clean up resources"""
        if self.stream:
            try:
                if self.stream.is_active():
                    self.stream.stop_stream()
                self.stream.close()
            except:
                pass
        if self.pyaudio:
            try:
                self.pyaudio.terminate()
            except:
                pass


async def main():
    """Run transcription test"""
    
    # Get API key
    api_key = config.DEEPGRAM_API_KEY
    if not api_key or api_key == "":
        print("❌ No API key found in config.py")
        print("\nPlease set DEEPGRAM_API_KEY in config.py")
        print("Get a free key from: https://console.deepgram.com/signup")
        return
    
    # Get test duration from command line or use default
    duration = 30.0
    if len(sys.argv) > 1:
        try:
            duration = float(sys.argv[1])
        except:
            print(f"Invalid duration: {sys.argv[1]}, using default 30s")
    
    # Create tester (device sample rate will be auto-detected)
    tester = TranscriptionTester(
        api_key=api_key,
        device_sample_rate=44100  # Initial value, will be updated by _find_microphone()
    )
    
    try:
        await tester.test_transcription(duration=duration)
    finally:
        tester.cleanup()


if __name__ == "__main__":
    print("\nUsage: python3 test_transcription.py [duration_in_seconds]")
    print("Example: python3 test_transcription.py 60  (test for 60 seconds)\n")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")

