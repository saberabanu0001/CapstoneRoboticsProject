#!/usr/bin/env python3
"""
YouTube Music Authentication Setup for Robot
Run this once to authenticate with YouTube Music
"""
from ytmusicapi import YTMusic

print("=" * 70)
print("  YOUTUBE MUSIC SETUP FOR ROVY")
print("=" * 70)
print()
print("This will authenticate your YouTube Music account.")
print()
print("You need to:")
print("1. Open YouTube Music in a browser on this Pi")
print("2. Log in with: nilyufarmobeius@gmail.com")
print("3. Open browser DevTools (F12)")
print("4. Go to Network tab")
print("5. Find any request to music.youtube.com")
print("6. Copy the 'Cookie' header")
print()
print("Or use the interactive setup...")
print()

try:
    # Try interactive browser-based setup (easier)
    print("Attempting browser-based setup...")
    YTMusic.setup(filepath="ytmusic_auth.json", headers_raw="")
    print()
    print("=" * 70)
    print("✅ SETUP COMPLETE!")
    print("=" * 70)
    print()
    print("Authentication saved to: ytmusic_auth.json")
    print("Now when you say 'play music', it will use YouTube Music!")
    print()
except Exception as e:
    print(f"Error: {e}")
    print()
    print("Manual setup needed:")
    print("Run: ytmusicapi setup")
    print("Follow the prompts to paste browser headers")

