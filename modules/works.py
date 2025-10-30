# from transformers import AutoModelForCausalLM, AutoTokenizer
# import torch
# import time

# # Model initialization optimized for Jetson
# # Using TinyLlama-1.1B - optimized for edge devices, better than Sheared-LLaMA
# model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
# device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# print(f"Using device: {device}")

# # Jetson-specific optimizations (fully on GPU with minimal memory)
# if device.type == "cuda":
#     # Enable TF32 for faster computation on Jetson (Ampere architecture)
#     torch.backends.cuda.matmul.allow_tf32 = True
#     torch.backends.cudnn.allow_tf32 = True
    
#     # Clear CUDA cache before loading
#     torch.cuda.empty_cache()
    
#     print(f"Loading {model_name} - FULLY on GPU (no limits)...")
#     print("Using 16GB unified memory - plenty of room for LLM + object detection!")
    
#     # Load model FULLY on GPU without any memory limits
#     # Jetson has 16GB unified memory - no need for restrictions
#     model = AutoModelForCausalLM.from_pretrained(
#         model_name,
#         torch_dtype=torch.float16,
#         device_map={"": 0},  # Force ALL layers to GPU 0
#         low_cpu_mem_usage=True,
#     )
    
#     gpu_mem_gb = torch.cuda.memory_allocated() / 1024**3
#     available_gb = 16.0 - gpu_mem_gb - 1.0  # Total - model - OS overhead
    
#     print(f"✓ Model loaded FULLY on GPU!")
#     print(f"  Model: {model_name} (1.1B parameters)")
#     print(f"  Precision: float16")
#     print(f"  ALL layers on GPU: 100%")
#     print(f"  GPU memory used by model: {gpu_mem_gb:.2f} GB")
#     print(f"  Available for object detection + camera: ~{available_gb:.1f} GB")
#     print(f"  Total unified memory: 16 GB")
    
#     # Set to eval mode
#     model.eval()
# else:
#     model = AutoModelForCausalLM.from_pretrained(model_name)
#     model.to(device)
#     model.eval()

# # Load tokenizer (moved after model for better timing measurement)
# tokenizer = AutoTokenizer.from_pretrained(model_name)
# if tokenizer.pad_token is None:
#     tokenizer.pad_token = tokenizer.eos_token

# # Warmup run to initialize CUDA kernels (improves actual inference time)
# if device.type == "cuda":
#     print("Warming up GPU...")
#     warmup_prompt = "Test"
#     warmup_inputs = tokenizer(warmup_prompt, return_tensors="pt").to(device)
#     with torch.no_grad():
#         _ = model.generate(**warmup_inputs, max_new_tokens=5)
#     torch.cuda.synchronize()  # Wait for GPU operations to complete
#     print("Warmup complete")

# # Clear cache before actual inference
# if device.type == "cuda":
#     torch.cuda.empty_cache()

# # Start timing after warmup
# start_time = time.time()

# prompt = (
#     "Answer in a very short and concise manner. Put the most relevant and important information in one well-structured sentence.\n"
#     "Question: What is Tajmahal?\n"
#     "Answer:"
# )

# # Tokenize input
# inputs = tokenizer(prompt, return_tensors="pt").to(device)

# # Generate with optimized parameters for Jetson
# with torch.no_grad():
#     # Use torch.amp for automatic mixed precision if needed
#     if device.type == "cuda":
#         with torch.amp.autocast('cuda'):
#             outputs = model.generate(
#                 **inputs,
#                 max_new_tokens=90,
#                 do_sample=False,
#                 num_beams=1,  # Greedy decoding (fastest)
#                 eos_token_id=tokenizer.eos_token_id,
#                 pad_token_id=tokenizer.pad_token_id,
#                 repetition_penalty=1.2,
#                 no_repeat_ngram_size=3,
#                 use_cache=True  # Reuse KV cache
#             )
#     else:
#         outputs = model.generate(
#             **inputs,
#             max_new_tokens=90,
#             do_sample=False,
#             num_beams=1,
#             eos_token_id=tokenizer.eos_token_id,
#             pad_token_id=tokenizer.pad_token_id,
#             repetition_penalty=1.2,
#             no_repeat_ngram_size=3
#         )

# # Ensure GPU operations are complete before timing
# if device.type == "cuda":
#     torch.cuda.synchronize()

# end_time = time.time()

# # Decode output
# generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

# if "Answer:" in generated_text:
#     answer = generated_text.split("Answer:")[-1].strip()
#     if '\n' in answer:
#         answer = answer.split('\n')[0].strip()
    
#     sentence_endings = ['.', '!', '?']
#     # Find the position of the *last* sentence-ending punctuation
#     end_pos = max(answer.rfind(char) for char in sentence_endings)
#     if end_pos != -1:
#         answer = answer[:end_pos + 1].strip()
    
#     print(f"Answer: {answer}")
#     print(f"Length: {len(answer)} characters")
# else:
#     print(f"Generated text: {generated_text}")

# elapsed_time = end_time - start_time
# print(f"Time to execute: {elapsed_time:.4f} seconds")

# # Print memory usage statistics
# if device.type == "cuda":
#     peak_gb = torch.cuda.max_memory_allocated() / 1024**3
#     current_gb = torch.cuda.memory_allocated() / 1024**3
#     available_gb = 16.0 - current_gb - 1.0  # 16GB total - model - OS
    
#     print(f"\n{'='*60}")
#     print(f"GPU Memory Stats (16GB Unified Memory):")
#     print(f"  Peak usage: {peak_gb:.2f} GB")
#     print(f"  Current usage: {current_gb:.2f} GB")
#     print(f"  Available for object detection: ~{available_gb:.1f} GB")
#     print(f"  Total unified memory: 16 GB")
#     print(f"{'='*60}")

import whisper
import torch
import sounddevice as sd
import numpy as np
import queue
import sys
from threading import Thread, Event
from TTS.api import TTS
import soundfile as sf
from rover_controller import Rover
import time
import serial 

# Parameters
SAMPLE_RATE = 16000  # 16kHz sample rate
CHUNK_DURATION = 5   # seconds
BLOCKSIZE = 1024     # frames per callback

# Load models
print("Loading Whisper model...")
try:
    whisper_model = whisper.load_model("base")
    print("✓ Whisper model loaded successfully!")
except Exception as e:
    print(f"Error loading Whisper model: {e}")
    sys.exit(1)

print("Loading TTS model...")
try:
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tts_model = TTS(model_name="tts_models/en/ljspeech/fast_pitch").to(device)
    print("✓ TTS model loaded successfully!")
except Exception as e:
    print(f"Error loading TTS model: {e}")
    sys.exit(1)

rover = Rover('/dev/ttyACM0')
print("Rover is initialized")

# Queues and events
audio_queue = queue.Queue(maxsize=100)
response_queue = queue.Queue()
stop_event = Event()
is_speaking = Event()  # Flag to prevent recording while speaking

def audio_callback(indata, frames, time_info, status):
    """Called for each audio chunk from the microphone"""
    if status:
        print(f"Audio callback status: {status}", file=sys.stderr)

    # Don't record while the assistant is speaking
    if is_speaking.is_set():
        return

    # Instead of dropping frames, use a non-blocking put with clear fallback
    try:
        audio_queue.put_nowait(indata.copy())
    except queue.Full:
        audio_queue.queue.clear()  # Clear old data to keep latency low
        print("⚠️ Audio queue full — cleared buffer to avoid delay", file=sys.stderr)

def process_user_input(text):
    """Process user input and generate response"""
    if not text.strip():
        return None
    
    text_lower = text.lower().strip()
    
    # Check for specific prompts/commands
    if "move command turn left" in text_lower or "move command left" in text_lower or "move command move left" in text_lower:
        rover.move('left', distance_m=0.5, speed_label='slow')
        time.sleep(1)
        return
    elif "move command forward" in text_lower or "move command move forward" in text_lower or "move command move straight" in text_lower:
        rover.move('forward', distance_m=1.0, speed_label='medium')
        time.sleep(1)
        return
    
    elif "move command turn right" in text_lower or "move command right" in text_lower or "move command move right" in text_lower:
        rover.move('right', distance_m=0.5, speed_label='slow')
        time.sleep(1)
        return
    
    elif "move command backward" in text_lower or "move command move backward" in text_lower or "move command backward" in text_lower:
        rover.move('backward', distance_m=0.8, speed_label='fast')
        time.sleep(1)
        return
    
    elif "what time is it" in text_lower or "what's the time" in text_lower or "tell me the time" in text_lower:
        current_time = time.strftime("%I:%M %p")
        return f"The current time is {current_time}."
    
    elif "what day is it" in text_lower or "what's the date" in text_lower or "today's date" in text_lower:
        current_date = time.strftime("%A, %B %d, %Y")
        return f"Today is {current_date}."
    
    elif "bye" in text_lower or "goodbye" in text_lower or "see you" in text_lower:
        return "Goodbye! Have a wonderful day!"
    
    else:
        # Echo back what was said if no specific prompt is detected
        return text

def speak_text(text):
    """Convert text to speech and play it"""
    if not text:
        return
    try:
        is_speaking.set()
        print(f"\n🔊 Assistant: {text}\n")

        temp_file = "temp_response.wav"

        # Generate speech first (before stopping audio recording too long)
        tts_model.tts_to_file(text=text, file_path=temp_file)

        # Then play the result
        audio_data, sample_rate = sf.read(temp_file)
        sd.play(audio_data, sample_rate)
        sd.wait()
        time.sleep(0.25)
    except Exception as e:
        print(f"Error in TTS: {e}", file=sys.stderr)
    finally:
        is_speaking.clear()


def response_handler():
    """Handle responses from the response queue"""
    while not stop_event.is_set():
        try:
            response_text = response_queue.get(timeout=0.5)
            speak_text(response_text)
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Error in response handler: {e}", file=sys.stderr)

def transcribe_audio():
    """Continuously transcribe audio from the queue"""
    buffer = []
    frames_needed = int(SAMPLE_RATE * CHUNK_DURATION)
    
    while not stop_event.is_set():
        try:
            chunk = audio_queue.get(timeout=0.5)
            buffer.append(chunk)
            
            current_length = sum(len(c) for c in buffer)
            
            if current_length >= frames_needed:
                # Concatenate all chunks
                audio_np = np.concatenate(buffer, axis=0)
                audio_np = audio_np[:frames_needed]
                
                # Convert stereo to mono if needed
                if audio_np.ndim > 1:
                    audio_np = np.mean(audio_np, axis=1)
                
                audio_np = audio_np.flatten()
                
                # Ensure float32 in range [-1, 1]
                if audio_np.dtype != np.float32:
                    audio_np = audio_np.astype(np.float32)
                
                max_val = np.abs(audio_np).max()
                if max_val > 1.0:
                    audio_np = audio_np / max_val
                
                # Check if audio has significant content (not silence)
                if max_val < 0.01:  # Very quiet, likely silence
                    buffer = []
                    continue
                
                # Transcribe
                try:
                    result = whisper_model.transcribe(
                        audio_np,
                        language='en',
                        fp16=torch.cuda.is_available()
                    )
                    
                    text = result['text'].strip()
                    if text:
                        print(f"👤 You: {text}")
                        
                        # Process input and generate response
                        response = process_user_input(text)
                        if response:
                            response_queue.put(response)
                    
                except Exception as e:
                    print(f"Transcription error: {e}", file=sys.stderr)
                
                buffer = []
                
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Error in transcription loop: {e}", file=sys.stderr)

def main():
    """Main function to start the voice assistant"""
    print(f"\n{'='*60}")
    print(f"🎙️  VOICE ASSISTANT SYSTEM")
    print(f"{'='*60}")
    print(f"Sample Rate: {SAMPLE_RATE} Hz")
    print(f"Chunk Duration: {CHUNK_DURATION} seconds")
    print(f"Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
    print(f"\nPress Ctrl+C to stop")
    print(f"{'='*60}\n")
    
    # Start threads
    transcription_thread = Thread(target=transcribe_audio, daemon=True)
    response_thread = Thread(target=response_handler, daemon=True)
    
    transcription_thread.start()
    response_thread.start()
    
    try:
        sd.default.latency = ('low', 'low') 
        with sd.InputStream(
            channels=1,
            samplerate=SAMPLE_RATE,
            blocksize=BLOCKSIZE,
            callback=audio_callback,
            dtype=np.float32
        ):
            print("🎤 Listening... Speak into the microphone.\n")
            
            # Initial greeting
            response_queue.put("Hello")
            
            # Keep main thread alive
            while True:
                sd.sleep(1000)
                
    except KeyboardInterrupt:
        print("\n\n" + "="*60)

if __name__ == "__main__":
    main()
#     print("Stopping voice assistant...")
#     stop_event.set()
#     transcription_thread.join(timeout=2)
#     response_thread.join(timeout=2)
#     print("✓ Voice assistant stopped successfully!")
#     print("="*60)
# except Exception as e:
#     print(f"\nError: {e}")
#     stop_event.set()
#     sys.exit(1)


# import whisper
# import torch
# import sounddevice as sd
# import numpy as np
# import queue
# import sys
# from threading import Thread, Event
# from TTS.api import TTS
# import soundfile as sf
# import time
# from rover_controller import Rover
# import time
# import serial 

# # Parameters
# SAMPLE_RATE = 16000  # 16kHz sample rate
# CHUNK_DURATION = 5   # seconds
# BLOCKSIZE = 1024     # frames per callback

# # Load models
# print("Loading Whisper model...")
# try:
#     whisper_model = whisper.load_model("base")
#     print("✓ Whisper model loaded successfully!")
# except Exception as e:
#     print(f"Error loading Whisper model: {e}")
#     sys.exit(1)

# print("Loading TTS model...")
# try:
#     device = "cuda" if torch.cuda.is_available() else "cpu"
#     tts_model = TTS(model_name="tts_models/en/ljspeech/fast_pitch").to(device)
#     print("✓ TTS model loaded successfully!")
# except Exception as e:
#     print(f"Error loading TTS model: {e}")
#     sys.exit(1)

# rover = Rover('/dev/tty.usbmodem58FA0943761')
# print("Rover is initialized")

# # Queues and events
# audio_queue = queue.Queue(maxsize=100)
# response_queue = queue.Queue()
# stop_event = Event()
# is_speaking = Event()  # Flag to prevent recording while speaking

# def audio_callback(indata, frames, time_info, status):
#     """Called for each audio chunk from the microphone"""
#     if status:
#         print(f"Audio callback status: {status}", file=sys.stderr)
    
#     # Don't record while the assistant is speaking
#     if is_speaking.is_set():
#         return
    
#     try:
#         audio_queue.put(indata.copy(), timeout=0.1)
#     except queue.Full:
#         print("Warning: Audio queue full, dropping frame", file=sys.stderr)

# def process_user_input(text):
#     """Process user input and generate response"""
#     if not text.strip():
#         return None
    
#     text_lower = text.lower().strip()
    
#     # Check for specific prompts/commands
#     if "move command turn left" in text_lower or "move command left" in text_lower or "move command move left" in text_lower:
#         rover.move('left', distance_m=0.5, speed_label='slow')
#         time.sleep(1)
#         return
#     elif "move command forward" in text_lower or "move command move forward" in text_lower or "move command move straight" in text_lower:
#         rover.move('forward', distance_m=1.0, speed_label='medium')
#         time.sleep(1)
#         return
    
#     elif "move command turn right" in text_lower or "move command right" in text_lower or "move command move right" in text_lower:
#         rover.move('right', distance_m=0.5, speed_label='slow')
#         time.sleep(1)
#         return
    
#     elif "move command backward" in text_lower or "move command move backward" in text_lower or "move command backward" in text_lower:
#         rover.move('backward', distance_m=0.8, speed_label='fast')
#         time.sleep(1)
#         return
    
#     elif "what time is it" in text_lower or "what's the time" in text_lower or "tell me the time" in text_lower:
#         current_time = time.strftime("%I:%M %p")
#         return f"The current time is {current_time}."
    
#     elif "what day is it" in text_lower or "what's the date" in text_lower or "today's date" in text_lower:
#         current_date = time.strftime("%A, %B %d, %Y")
#         return f"Today is {current_date}."
    
#     elif "bye" in text_lower or "goodbye" in text_lower or "see you" in text_lower:
#         return "Goodbye! Have a wonderful day!"
    
#     else:
#         # Echo back what was said if no specific prompt is detected
#         return text

# def speak_text(text):
#     """Convert text to speech and play it"""
#     if not text:
#         return
    
#     try:
#         is_speaking.set()  # Set flag to stop recording
        
#         print(f"\n🔊 Assistant: {text}\n")
        
#         # Generate speech to a temporary file
#         temp_file = "temp_response.wav"
#         tts_model.tts_to_file(text=text, file_path=temp_file)
        
#         # Read the audio file
#         audio_data, sample_rate = sf.read(temp_file)
        
#         # Play the audio
#         sd.play(audio_data, sample_rate)
#         sd.wait()  # Wait until audio finishes playing
        
#         time.sleep(0.5)  # Small pause after speaking
        
#     except Exception as e:
#         print(f"Error in TTS: {e}", file=sys.stderr)
#     finally:
#         is_speaking.clear()  # Clear flag to resume recording

# def response_handler():
#     """Handle responses from the response queue"""
#     while not stop_event.is_set():
#         try:
#             response_text = response_queue.get(timeout=0.5)
#             speak_text(response_text)
#         except queue.Empty:
#             continue
#         except Exception as e:
#             print(f"Error in response handler: {e}", file=sys.stderr)

# def transcribe_audio():
#     """Continuously transcribe audio from the queue"""
#     buffer = []
#     frames_needed = int(SAMPLE_RATE * CHUNK_DURATION)
    
#     while not stop_event.is_set():
#         try:
#             chunk = audio_queue.get(timeout=0.5)
#             buffer.append(chunk)
            
#             current_length = sum(len(c) for c in buffer)
            
#             if current_length >= frames_needed:
#                 # Concatenate all chunks
#                 audio_np = np.concatenate(buffer, axis=0)
#                 audio_np = audio_np[:frames_needed]
                
#                 # Convert stereo to mono if needed
#                 if audio_np.ndim > 1:
#                     audio_np = np.mean(audio_np, axis=1)
                
#                 audio_np = audio_np.flatten()
                
#                 # Ensure float32 in range [-1, 1]
#                 if audio_np.dtype != np.float32:
#                     audio_np = audio_np.astype(np.float32)
                
#                 max_val = np.abs(audio_np).max()
#                 if max_val > 1.0:
#                     audio_np = audio_np / max_val
                
#                 # Check if audio has significant content (not silence)
#                 if max_val < 0.01:  # Very quiet, likely silence
#                     buffer = []
#                     continue
                
#                 # Transcribe
#                 try:
#                     result = whisper_model.transcribe(
#                         audio_np,
#                         language='en',
#                         fp16=torch.cuda.is_available()
#                     )
                    
#                     text = result['text'].strip()
#                     if text:
#                         print(f"👤 You: {text}")
                        
#                         # Process input and generate response
#                         response = process_user_input(text)
#                         if response:
#                             response_queue.put(response)
                    
#                 except Exception as e:
#                     print(f"Transcription error: {e}", file=sys.stderr)
                
#                 buffer = []
                
#         except queue.Empty:
#             continue
#         except Exception as e:
#             print(f"Error in transcription loop: {e}", file=sys.stderr)

# def main():
#     """Main function to start the voice assistant"""
#     print(f"\n{'='*60}")
#     print(f"🎙️  VOICE ASSISTANT SYSTEM")
#     print(f"{'='*60}")
#     print(f"Sample Rate: {SAMPLE_RATE} Hz")
#     print(f"Chunk Duration: {CHUNK_DURATION} seconds")
#     print(f"Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
#     print(f"\nPress Ctrl+C to stop")
#     print(f"{'='*60}\n")
    
#     # Start threads
#     transcription_thread = Thread(target=transcribe_audio, daemon=True)
#     response_thread = Thread(target=response_handler, daemon=True)
    
#     transcription_thread.start()
#     response_thread.start()
    
#     try:
#         with sd.InputStream(
#             channels=1,
#             samplerate=SAMPLE_RATE,
#             blocksize=BLOCKSIZE,
#             callback=audio_callback,
#             dtype=np.float32
#         ):
#             print("🎤 Listening... Speak into the microphone.\n")
            
#             # Initial greeting
#             response_queue.put("Hello")
            
#             # Keep main thread alive
#             while True:
#                 sd.sleep(1000)
                
#     except KeyboardInterrupt:
#         print("\n\n" + "="*60)
#         print("Stopping voice assistant...")
#         stop_event.set()
#         transcription_thread.join(timeout=2)
#         response_thread.join(timeout=2)
#         print("✓ Voice assistant stopped successfully!")
#         print("="*60)
#     except Exception as e:
#         print(f"\nError: {e}")
#         stop_event.set()
#         sys.exit(1)

# if __name__ == "__main__":
#     main()