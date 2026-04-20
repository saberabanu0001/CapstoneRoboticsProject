#!/bin/bash
# Set microphone gain for better distant speech detection

# USB Microphone is on card 4
MIC_CARD=4

echo "🎤 Setting microphone gain for distant speech detection..."

# Set microphone capture volume to maximum (100%)
amixer -c $MIC_CARD sset 'Mic' 100% 2>/dev/null || echo "⚠️  'Mic' control not found"

# Set capture volume to maximum
amixer -c $MIC_CARD sset 'Capture' 100% 2>/dev/null || echo "⚠️  'Capture' control not found"

# Enable auto gain control if available
amixer -c $MIC_CARD sset 'Auto Gain Control' on 2>/dev/null || echo "⚠️  'Auto Gain Control' not found (this is OK)"

# Set PCM capture volume
amixer -c $MIC_CARD sset 'PCM' 100% 2>/dev/null || echo "⚠️  'PCM' control not found"

# Display current settings
echo ""
echo "📊 Current microphone settings (Card $MIC_CARD):"
amixer -c $MIC_CARD 2>/dev/null | grep -E "(Mic|Capture)" || echo "No detailed info available"

echo ""
echo "✅ Microphone gain settings applied!"
echo "💡 The microphone should now be more sensitive to distant speech."

