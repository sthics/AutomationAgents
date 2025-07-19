#!/usr/bin/env python3
"""
Spotify Agent
Handles Spotify operations with AI assistance
"""

import os
import json
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from typing import Dict, Any, List, Optional
from datetime import datetime

from base_agent import BaseAgent

class SpotifyAgent(BaseAgent):
    """Spotify AI Agent for music management"""
    
    # Spotify API scopes
    SCOPES = [
        'user-read-playback-state',
        'user-modify-playback-state',
        'user-read-currently-playing',
        'playlist-read-private',
        'playlist-read-collaborative',
        'playlist-modify-private',
        'playlist-modify-public',
        'user-library-read',
        'user-library-modify',
        'user-read-recently-played',
        'user-top-read'
    ]
    
    def __init__(self):
        super().__init__("spotify")
        self.client_id = os.getenv('SPOTIFY_CLIENT_ID')
        self.client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        self.redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI', 'https://example.com/callback')
        
        if not self.client_id or not self.client_secret:
            raise ValueError("Spotify credentials not found. Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET")
        
        self.sp = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Spotify API"""
        try:
            auth_manager = SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
                scope=' '.join(self.SCOPES),
                cache_path=".spotify_cache"
            )
            
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            self.logger.info("Spotify authentication successful")
            
        except Exception as e:
            self.logger.error(f"Spotify authentication failed: {e}")
            raise
    
    def _test_service_connection(self) -> bool:
        """Test Spotify API connection"""
        try:
            user = self.sp.current_user()
            self.logger.info(f"Connected to Spotify account: {user['display_name']}")
            return True
        except Exception as e:
            self.logger.error(f"Spotify connection test failed: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get Spotify account status"""
        try:
            user = self.sp.current_user()
            playback = self.sp.current_playback()
            
            status = {
                'user_id': user['id'],
                'display_name': user['display_name'],
                'followers': user['followers']['total'],
                'country': user['country'],
                'subscription': user.get('product', 'free'),
                'status': 'connected'
            }
            
            if playback:
                status['currently_playing'] = {
                    'track': playback['item']['name'] if playback['item'] else 'Unknown',
                    'artist': playback['item']['artists'][0]['name'] if playback['item'] else 'Unknown',
                    'is_playing': playback['is_playing'],
                    'device': playback['device']['name']
                }
            
            return status
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}
    
    def get_current_track(self) -> Dict[str, Any]:
        """Get currently playing track"""
        try:
            playback = self.sp.current_playback()
            if not playback or not playback['item']:
                return {'status': 'no_track_playing'}
            
            track = playback['item']
            return {
                'name': track['name'],
                'artist': track['artists'][0]['name'],
                'album': track['album']['name'],
                'is_playing': playback['is_playing'],
                'progress': playback['progress_ms'],
                'duration': track['duration_ms'],
                'device': playback['device']['name']
            }
            
        except Exception as e:
            self.logger.error(f"Error getting current track: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def search_tracks(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for tracks"""
        try:
            results = self.sp.search(q=query, type='track', limit=limit)
            tracks = []
            
            for track in results['tracks']['items']:
                tracks.append({
                    'id': track['id'],
                    'name': track['name'],
                    'artist': track['artists'][0]['name'],
                    'album': track['album']['name'],
                    'duration_ms': track['duration_ms'],
                    'popularity': track['popularity'],
                    'preview_url': track['preview_url']
                })
            
            self.log_action("search_tracks", f"Found {len(tracks)} tracks for: {query}")
            return tracks
            
        except Exception as e:
            self.logger.error(f"Error searching tracks: {e}")
            return []
    
    def get_recommendations(self, seed_tracks: List[str] = None, seed_artists: List[str] = None, 
                          seed_genres: List[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Get music recommendations"""
        try:
            # If no seeds provided, use current top tracks
            if not any([seed_tracks, seed_artists, seed_genres]):
                top_tracks = self.sp.current_user_top_tracks(limit=5, time_range='short_term')
                seed_tracks = [track['id'] for track in top_tracks['items']]
            
            recommendations = self.sp.recommendations(
                seed_tracks=seed_tracks,
                seed_artists=seed_artists,
                seed_genres=seed_genres,
                limit=limit
            )
            
            tracks = []
            for track in recommendations['tracks']:
                tracks.append({
                    'id': track['id'],
                    'name': track['name'],
                    'artist': track['artists'][0]['name'],
                    'album': track['album']['name'],
                    'popularity': track['popularity']
                })
            
            self.log_action("get_recommendations", f"Generated {len(tracks)} recommendations")
            return tracks
            
        except Exception as e:
            self.logger.error(f"Error getting recommendations: {e}")
            return []
    
    def create_playlist(self, name: str, description: str = "", public: bool = False) -> Dict[str, Any]:
        """Create a new playlist"""
        try:
            user_id = self.sp.current_user()['id']
            playlist = self.sp.user_playlist_create(
                user=user_id,
                name=name,
                public=public,
                description=description
            )
            
            result = {
                'id': playlist['id'],
                'name': playlist['name'],
                'url': playlist['external_urls']['spotify'],
                'description': playlist['description']
            }
            
            self.log_action("create_playlist", f"Created playlist: {name}")
            return result
            
        except Exception as e:
            self.logger.error(f"Error creating playlist: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def add_tracks_to_playlist(self, playlist_id: str, track_ids: List[str]) -> bool:
        """Add tracks to a playlist"""
        try:
            self.sp.playlist_add_items(playlist_id, track_ids)
            self.log_action("add_tracks_to_playlist", f"Added {len(track_ids)} tracks to playlist")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding tracks to playlist: {e}")
            return False
    
    def _get_ai_track_suggestions(self, mood: str) -> List[str]:
        """Get track suggestions for a mood from the AI."""
        prompt = f"""
        Create a list of music recommendations for someone feeling {mood}.
        Provide 10-15 song suggestions in this format:
        - "Song Name" by Artist Name
        Focus on songs that match the {mood} mood. Include a mix of popular and lesser-known tracks.
        """
        
        ai_suggestions = self.ask_ai(prompt)
        track_ids = []
        lines = ai_suggestions.split('\n')
        
        for line in lines:
            if line.strip().startswith( ('-', '•') ):
                song_info = line.strip().lstrip('-•').strip()
                if ' by ' in song_info:
                    song_name, artist = song_info.split(' by ', 1)
                    song_name = song_name.strip().strip('"')
                    artist = artist.strip()
                    
                    search_results = self.search_tracks(f"{song_name} {artist}", limit=1)
                    if search_results:
                        track_ids.append(search_results[0]['id'])
        return track_ids

    def _get_genre_recommendations(self, mood: str, limit: int) -> List[str]:
        """Get track recommendations based on mood-mapped genres."""
        genre_map = {
            'happy': ['pop', 'dance', 'funk'],
            'sad': ['indie', 'blues', 'singer-songwriter'],
            'energetic': ['rock', 'electronic', 'hip-hop'],
            'chill': ['ambient', 'jazz', 'indie-folk'],
            'focus': ['classical', 'ambient', 'instrumental']
        }
        genres = genre_map.get(mood.lower(), ['pop'])
        recommendations = self.get_recommendations(seed_genres=genres, limit=limit)
        return [rec['id'] for rec in recommendations]

    def create_mood_playlist(self, mood: str, limit: int = 20) -> Dict[str, Any]:
        """Create a playlist based on mood using AI and genre recommendations."""
        try:
            self.log_action("create_mood_playlist", f"Starting playlist creation for mood: {mood}")
            
            # Step 1: Get initial suggestions from AI
            track_ids = self._get_ai_track_suggestions(mood)
            
            # Step 2: If not enough tracks, supplement with genre-based recommendations
            if len(track_ids) < 10:
                needed = limit - len(track_ids)
                genre_recs = self._get_genre_recommendations(mood, needed)
                for rec_id in genre_recs:
                    if rec_id not in track_ids:
                        track_ids.append(rec_id)

            if not track_ids:
                self.logger.warning("Could not find any tracks for the mood playlist.")
                return {'status': 'error', 'error': 'No tracks found'}

            # Step 3: Create the playlist
            playlist_name = f"{mood.title()} Vibes - {datetime.now().strftime('%Y-%m-%d')}"
            description = f"AI-generated playlist for a {mood} mood."
            playlist = self.create_playlist(playlist_name, description)

            if 'id' not in playlist:
                return playlist # Return the error from create_playlist

            # Step 4: Add tracks to the new playlist
            final_tracks = track_ids[:limit]
            self.add_tracks_to_playlist(playlist['id'], final_tracks)
            playlist['tracks_added'] = len(final_tracks)
            
            self.log_action("create_mood_playlist", f"Successfully created '{playlist_name}' with {len(final_tracks)} tracks.")
            return playlist

        except Exception as e:
            self.logger.error(f"Error creating mood playlist: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def get_my_playlists(self) -> List[Dict[str, Any]]:
        """Get user's playlists"""
        try:
            playlists = self.sp.current_user_playlists()
            result = []
            
            for playlist in playlists['items']:
                result.append({
                    'id': playlist['id'],
                    'name': playlist['name'],
                    'tracks_count': playlist['tracks']['total'],
                    'public': playlist['public'],
                    'description': playlist['description']
                })
            
            self.log_action("get_my_playlists", f"Retrieved {len(result)} playlists")
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting playlists: {e}")
            return []
    
    def play_track(self, track_id: str) -> bool:
        """Play a specific track"""
        try:
            self.sp.start_playback(uris=[f"spotify:track:{track_id}"])
            self.log_action("play_track", f"Started playing track: {track_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error playing track: {e}")
            return False
    
    def pause_playback(self) -> bool:
        """Pause current playback"""
        try:
            self.sp.pause_playback()
            self.log_action("pause_playback", "Paused playback")
            return True
            
        except Exception as e:
            self.logger.error(f"Error pausing playback: {e}")
            return False
    
    def resume_playback(self) -> bool:
        """Resume current playback"""
        try:
            self.sp.start_playback()
            self.log_action("resume_playback", "Resumed playback")
            return True
        except Exception as e:
            self.logger.error(f"Error resuming playback: {e}")
            return False

    def interactive_mode(self):
        """Interactive mode for Spotify agent"""
        print(f"\n🎵 Spotify Agent - Interactive Mode")
        print("Commands: 'current', 'search <query>', 'play <track_id>', 'pause', 'resume', 'quit'")

        while True:
            try:
                command = input("\n> ").strip()

                if command == 'quit':
                    break

                elif command == 'current':
                    track = self.get_current_track()
                    if track.get('name'):
                        print(f"\n▶️ Now Playing: {track['name']} by {track['artist']}")
                    else:
                        print("\n⏹️ Nothing is currently playing.")

                elif command.startswith('search '):
                    query = command.split(' ', 1)[1]
                    tracks = self.search_tracks(query)
                    if tracks:
                        print(f"\n🔍 Search results for '{query}':")
                        for i, t in enumerate(tracks, 1):
                            print(f"{i}. {t['name']} by {t['artist']} (ID: {t['id']})")
                    else:
                        print("No tracks found.")

                elif command.startswith('play '):
                    track_id = command.split(' ', 1)[1]
                    if self.play_track(track_id):
                        print(f"Playing track: {track_id}")

                elif command == 'pause':
                    self.pause_playback()
                    print("Playback paused.")

                elif command == 'resume':
                    self.resume_playback()
                    print("Playback resumed.")

                else:
                    print("Unknown command.")

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"An error occurred: {e}")
        
if __name__ == "__main__":
    agent = SpotifyAgent()
    if agent.test_connection():
        agent.interactive_mode()
    else:
        print("Failed to connect to Spotify")