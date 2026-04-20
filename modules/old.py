from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import time

# Model initialization optimized for Jetson
# Using TinyLlama-1.1B - optimized for edge devices, better than Sheared-LLaMA
model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print(f"Using device: {device}")

# Jetson-specific optimizations (fully on GPU with minimal memory)
if device.type == "cuda":
    # Enable TF32 for faster computation on Jetson (Ampere architecture)
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    
    # Clear CUDA cache before loading
    torch.cuda.empty_cache()
    
    print(f"Loading {model_name} - FULLY on GPU (no limits)...")
    print("Using 16GB unified memory - plenty of room for LLM + object detection!")
    
    # Load model FULLY on GPU without any memory limits
    # Jetson has 16GB unified memory - no need for restrictions
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.float16,
        device_map={"": 0},  # Force ALL layers to GPU 0
        low_cpu_mem_usage=True,
    )
    
    gpu_mem_gb = torch.cuda.memory_allocated() / 1024**3
    available_gb = 16.0 - gpu_mem_gb - 1.0  # Total - model - OS overhead
    
    print(f"✓ Model loaded FULLY on GPU!")
    print(f"  Model: {model_name} (1.1B parameters)")
    print(f"  Precision: float16")
    print(f"  ALL layers on GPU: 100%")
    print(f"  GPU memory used by model: {gpu_mem_gb:.2f} GB")
    print(f"  Available for object detection + camera: ~{available_gb:.1f} GB")
    print(f"  Total unified memory: 16 GB")
    
    # Set to eval mode
    model.eval()
else:
    model = AutoModelForCausalLM.from_pretrained(model_name)
    model.to(device)
    model.eval()

# Load tokenizer (moved after model for better timing measurement)
tokenizer = AutoTokenizer.from_pretrained(model_name)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

# Warmup run to initialize CUDA kernels (improves actual inference time)
if device.type == "cuda":
    print("Warming up GPU...")
    warmup_prompt = "Test"
    warmup_inputs = tokenizer(warmup_prompt, return_tensors="pt").to(device)
    with torch.no_grad():
        _ = model.generate(**warmup_inputs, max_new_tokens=5)
    torch.cuda.synchronize()  # Wait for GPU operations to complete
    print("Warmup complete")

# Clear cache before actual inference
if device.type == "cuda":
    torch.cuda.empty_cache()

# Start timing after warmup
start_time = time.time()

prompt = (
    "Answer in a very short and concise manner. Put the most relevant and important information in one well-structured sentence.\n"
    "Question: What is Tajmahal?\n"
    "Answer:"
)

# Tokenize input
inputs = tokenizer(prompt, return_tensors="pt").to(device)

# Generate with optimized parameters for Jetson
with torch.no_grad():
    # Use torch.amp for automatic mixed precision if needed
    if device.type == "cuda":
        with torch.amp.autocast('cuda'):
            outputs = model.generate(
                **inputs,
                max_new_tokens=90,
                do_sample=False,
                num_beams=1,  # Greedy decoding (fastest)
                eos_token_id=tokenizer.eos_token_id,
                pad_token_id=tokenizer.pad_token_id,
                repetition_penalty=1.2,
                no_repeat_ngram_size=3,
                use_cache=True  # Reuse KV cache
            )
    else:
        outputs = model.generate(
            **inputs,
            max_new_tokens=90,
            do_sample=False,
            num_beams=1,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
            repetition_penalty=1.2,
            no_repeat_ngram_size=3
        )

# Ensure GPU operations are complete before timing
if device.type == "cuda":
    torch.cuda.synchronize()

end_time = time.time()

# Decode output
generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

if "Answer:" in generated_text:
    answer = generated_text.split("Answer:")[-1].strip()
    if '\n' in answer:
        answer = answer.split('\n')[0].strip()
    
    sentence_endings = ['.', '!', '?']
    # Find the position of the *last* sentence-ending punctuation
    end_pos = max(answer.rfind(char) for char in sentence_endings)
    if end_pos != -1:
        answer = answer[:end_pos + 1].strip()
    
    print(f"Answer: {answer}")
    print(f"Length: {len(answer)} characters")
else:
    print(f"Generated text: {generated_text}")

elapsed_time = end_time - start_time
print(f"Time to execute: {elapsed_time:.4f} seconds")

# Print memory usage statistics
if device.type == "cuda":
    peak_gb = torch.cuda.max_memory_allocated() / 1024**3
    current_gb = torch.cuda.memory_allocated() / 1024**3
    available_gb = 16.0 - current_gb - 1.0  # 16GB total - model - OS
    
    print(f"\n{'='*60}")
    print(f"GPU Memory Stats (16GB Unified Memory):")
    print(f"  Peak usage: {peak_gb:.2f} GB")
    print(f"  Current usage: {current_gb:.2f} GB")
    print(f"  Available for object detection: ~{available_gb:.1f} GB")
    print(f"  Total unified memory: 16 GB")
    print(f"{'='*60}")