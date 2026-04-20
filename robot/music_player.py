#!/usr/bin/env python3
"""
YouTube Music Player for Rovy
Plays music from YouTube Music with genre support and dance integration
"""

import os
import subprocess
import random
import time
import threading
import json
from typing import Optional, List, Dict
from pathlib import Path

# Try to import ytmusicapi
try:
    from ytmusicapi import YTMusic
    YTMUSIC_OK = True
except ImportError:
    YTMUSIC_OK = False
    print("[Music] ytmusicapi not installed. Run: pip install ytmusicapi")


class MusicPlayer:
    """
    YouTube Music player with genre support and dance integration.
    """
    
    def __init__(self, auth_file: str = "ytmusic_oauth.json"):
        self.auth_file = auth_file
        self.yt_music = None
        self.current_song = None
        self.is_playing = False
        self.playback_process = None
        self.playback_thread = None
        
        # Genre playlists - curated for different moods
        self.genre_searches = {
            'dance': ['dance party hits', 'upbeat dance music', 'edm hits', 'party music'],
            'party': ['party hits', 'dance party', 'fun upbeat music', 'celebration songs'],
            'classical': ['classical music', 'beethoven', 'mozart', 'bach'],
            'jazz': ['jazz music', 'smooth jazz', 'jazz standards'],
            'rock': ['rock music', 'classic rock', 'rock hits'],
            'pop': ['pop music', 'top pop hits', 'pop songs'],
            'chill': ['chill music', 'relaxing music', 'lofi beats'],
            'electronic': ['electronic music', 'edm', 'techno', 'house music'],
            'fun': ['fun music', 'happy songs', 'upbeat music', 'feel good music']
        }
        
        # Initialize YouTube Music
        if YTMUSIC_OK:
            self._init_ytmusic()
        else:
            print("[Music] ⚠️ YouTube Music not available")
    
    def _init_ytmusic(self):
        """Initialize YouTube Music API."""
        try:
            if os.path.exists(self.auth_file):
                self.yt_music = YTMusic(self.auth_file)
                print("[Music] ✅ YouTube Music ready")
            else:
                print(f"[Music] ⚠️ Auth file not found: {self.auth_file}")
                print("[Music] Run: python setup_youtube_music.py or python auth_youtube.py")
        except Exception as e:
            print(f"[Music] ⚠️ Failed to initialize YouTube Music: {e}")
    
    def get_random_song(self, genre: str = 'dance') -> Optional[Dict]:
        """
        Get a random song for the specified genre.
        
        Args:
            genre: Genre name ('dance', 'classical', 'jazz', etc.)
        
        Returns:
            Dictionary with song info or None
        """
        if not self.yt_music:
            print("[Music] YouTube Music not initialized")
            return None
        
        try:
            # Get search terms for this genre
            search_terms = self.genre_searches.get(genre.lower(), self.genre_searches['dance'])
            search_query = random.choice(search_terms)
            
            print(f"[Music] Searching for: {search_query}")
            
            # Search for songs
            results = self.yt_music.search(search_query, filter='songs', limit=20)
            
            if not results:
                print("[Music] No results found")
                return None
            
            # Pick a random song from results
            song = random.choice(results)
            
            return {
                'video_id': song.get('videoId'),
                'title': song.get('title', 'Unknown'),
                'artist': song.get('artists', [{}])[0].get('name', 'Unknown') if song.get('artists') else 'Unknown',
                'duration': song.get('duration', '0:00'),
                'thumbnail': song.get('thumbnails', [{}])[-1].get('url', '') if song.get('thumbnails') else ''
            }
            
        except Exception as e:
            print(f"[Music] Error getting random song: {e}")
            return None
    
    def play_song(self, video_id: str, title: str = "Unknown", artist: str = "Unknown") -> bool:
        """
        Play a song from YouTube Music using yt-dlp and mpv.
        
        Args:
            video_id: YouTube video ID
            title: Song title
            artist: Artist name
        
        Returns:
            True if playback started successfully
        """
        if self.is_playing:
            print("[Music] Stopping current playback...")
            self.stop()
        
        try:
            self.current_song = {'title': title, 'artist': artist, 'video_id': video_id}
            self.is_playing = True
            
            print(f"[Music] 🎵 Playing: {title} by {artist}")
            
            # Use yt-dlp with mpv for best audio quality and reliability
            # yt-dlp extracts the audio stream URL, mpv plays it
            url = f"https://music.youtube.com/watch?v={video_id}"
            
            # Start playback in background thread
            self.playback_thread = threading.Thread(
                target=self._playback_worker,
                args=(url,),
                daemon=True
            )
            self.playback_thread.start()
            
            return True
            
        except Exception as e:
            print(f"[Music] Error starting playback: {e}")
            self.is_playing = False
            return False
    
    def _playback_worker(self, url: str):
        """Worker thread for audio playback."""
        try:
            # Try mpv first (best option)
            if self._check_command('mpv'):
                print("[Music] Using mpv for playback")
                self.playback_process = subprocess.Popen(
                    ['mpv', '--no-video', '--volume=70', url],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                self.playback_process.wait()
            
            # Fallback to yt-dlp + aplay
            elif self._check_command('yt-dlp'):
                print("[Music] Using yt-dlp + ffplay for playback")
                self.playback_process = subprocess.Popen(
                    ['yt-dlp', '-x', '--audio-format', 'best', '-o', '-', url, '|', 
                     'ffplay', '-nodisp', '-autoexit', '-'],
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                self.playback_process.wait()
            
            else:
                print("[Music] ⚠️ No playback method available (install mpv or yt-dlp)")
            
        except Exception as e:
            print(f"[Music] Playback error: {e}")
        
        finally:
            self.is_playing = False
            self.current_song = None
            self.playback_process = None
    
    def _check_command(self, cmd: str) -> bool:
        """Check if a command exists."""
        try:
            subprocess.run(['which', cmd], capture_output=True, check=True)
            return True
        except:
            return False
    
    def stop(self):
        """Stop current playback."""
        if self.playback_process:
            try:
                self.playback_process.terminate()
                self.playback_process.wait(timeout=2)
            except:
                try:
                    self.playback_process.kill()
                except:
                    pass
        
        self.is_playing = False
        self.current_song = None
        self.playback_process = None
        print("[Music] ⏹️ Playback stopped")
    
    def get_status(self) -> Dict:
        """Get current playback status."""
        return {
            'is_playing': self.is_playing,
            'current_song': self.current_song
        }
    
    def play_random(self, genre: str = 'dance') -> bool:
        """
        Play a random song from the specified genre.
        
        Args:
            genre: Genre name
        
        Returns:
            True if playback started
        """
        song = self.get_random_song(genre)
        
        if song:
            return self.play_song(
                song['video_id'],
                song['title'],
                song['artist']
            )
        else:
            print("[Music] Could not find a song to play")
            return False


# Global instance
_music_player: Optional[MusicPlayer] = None


def get_music_player() -> MusicPlayer:
    """Get or create the global music player instance."""
    global _music_player
    if _music_player is None:
        _music_player = MusicPlayer()
    return _music_player


# Quick test
if __name__ == "__main__":
    print("=" * 70)
    print("  ROVY MUSIC PLAYER TEST")
    print("=" * 70)
    
    player = MusicPlayer()
    
    if not player.yt_music:
        print("\n⚠️ YouTube Music not authenticated!")
        print("Run: python auth_youtube.py or python setup_youtube_music.py")
        exit(1)
    
    print("\nAvailable genres:")
    for genre in player.genre_searches.keys():
        print(f"  - {genre}")
    
    genre = input("\nEnter genre (or press Enter for 'dance'): ").strip() or 'dance'
    
    print(f"\nFinding random {genre} song...")
    song = player.get_random_song(genre)
    
    if song:
        print(f"\n🎵 Found: {song['title']} by {song['artist']}")
        print(f"   Duration: {song['duration']}")
        
        play = input("\nPlay this song? (y/N): ").strip().lower()
        if play == 'y':
            player.play_song(song['video_id'], song['title'], song['artist'])
            print("\nPlaying... Press Ctrl+C to stop")
            try:
                while player.is_playing:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping...")
                player.stop()
    else:
        print("\n❌ Could not find a song")

