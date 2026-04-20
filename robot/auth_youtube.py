#!/usr/bin/env python3
"""
YouTube Music OAuth Authentication
Generates URL to open on your phone, then paste callback URL back
"""
import json
import sys

# Load client secrets
try:
    with open('client_secrets.json', 'r') as f:
        secrets = json.load(f)
        client_id = secrets['installed']['client_id']
        client_secret = secrets['installed']['client_secret']
except Exception as e:
    print(f"Error loading client_secrets.json: {e}")
    sys.exit(1)

print("=" * 70)
print("  YOUTUBE MUSIC AUTHENTICATION")
print("=" * 70)
print()
print("Client ID:", client_id[:50] + "...")
print()

from ytmusicapi.auth.oauth.credentials import OAuthCredentials
from ytmusicapi.auth.oauth.token import RefreshingToken

# Create OAuth credentials
oauth_creds = OAuthCredentials(client_id=client_id, client_secret=client_secret)

# Get authorization URL
auth_url = oauth_creds.get_code()

print("=" * 70)
print("STEP 1: Open this URL on your phone or PC:")
print("=" * 70)
print()
print(auth_url)
print()
print("=" * 70)
print("STEP 2: Log in and click 'Allow'")
print("STEP 3: You'll see a code or be redirected to localhost")
print("STEP 4: Copy the FULL URL or just the 'code=' part")
print("=" * 70)
print()

# Get the code from user
code = input("Paste the code or full URL here: ").strip()

# Extract just the code if they pasted full URL
if "code=" in code:
    code = code.split("code=")[1].split("&")[0]

print()
print("Getting access token...")

try:
    # Exchange code for token
    token_response = oauth_creds.token_from_code(code)
    
    # Create refreshing token
    token = RefreshingToken.from_token_response(oauth_creds, token_response)
    
    # Save to file
    token.store_token(filepath="ytmusic_oauth.json")
    
    print()
    print("=" * 70)
    print("✅ SUCCESS! YouTube Music authenticated!")
    print("=" * 70)
    print()
    print("✅ Token saved to: ytmusic_oauth.json")
    print("✅ ROVY can now play YouTube Music!")
    print()
    print("Say 'play music' to your robot and it will play from YouTube Music! 🎵")
    print()
    
except Exception as e:
    print(f"Error: {e}")
    print()
    print("If you got an error, make sure:")
    print("1. YouTube Data API v3 is enabled")
    print("2. Your OAuth client has redirect URI: http://localhost")
    print("3. You copied the full code correctly")

