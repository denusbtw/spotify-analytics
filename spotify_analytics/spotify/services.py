import base64
import time
from collections import Counter
from datetime import timedelta

import requests
from allauth.socialaccount.models import SocialToken, SocialApp
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception, retry_if_exception_type


class SpotifyService:
    def __init__(self, user=None):
        self.user = user
        self.token = None

        if user:
            self.token = self.get_user_token()
        else:
            self.token = self.get_app_token()

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(requests.RequestException)
    )
    def fetch_batch(self, batch_ids: list[str]):
        headers = {"Authorization": f"Bearer {self.token}"}
        r = requests.get(
            "https://api.spotify.com/v1/tracks",
            params={"ids": ",".join(batch_ids)},
            headers=headers,
            timeout=10
        )

        if r.status_code == 429:
            retry_after = int(r.headers.get("Retry-After", 1))
            print(f"Rate limited, sleeping {retry_after}s")
            time.sleep(retry_after)
            raise requests.RequestException("429 Rate limit")

        r.raise_for_status()
        return r.json().get("tracks", [])

    def get_tracks(self, spotify_ids: list[str]):
        BATCH_SIZE = 50
        tracks = []

        for i in range(0, len(spotify_ids), BATCH_SIZE):
            batch = spotify_ids[i:i + BATCH_SIZE]
            batch_tracks = self.fetch_batch(batch)
            tracks.extend(batch_tracks)

        return tracks

    def get_artists(self, spotify_ids: list[str]):
        BATCH_SIZE = 50
        headers = {"Authorization": f"Bearer {self.token}"}
        tracks = []

        for i in range(0, len(spotify_ids), BATCH_SIZE):
            batch = spotify_ids[i:i + BATCH_SIZE]
            r = requests.get(
                "https://api.spotify.com/v1/artists",
                params={"ids": ",".join(batch)},
                headers=headers
            )
            if r.status_code == 200:
                tracks.extend(r.json().get("artists", []))
            else:
                print(f"Spotify API Error: {r.text}")
        return tracks

    def get_albums(self, spotify_ids: list[str]):
        BATCH_SIZE = 50
        headers = {"Authorization": f"Bearer {self.token}"}
        tracks = []

        for i in range(0, len(spotify_ids), BATCH_SIZE):
            batch = spotify_ids[i:i + BATCH_SIZE]
            r = requests.get(
                "https://api.spotify.com/v1/albums",
                params={"ids": ",".join(batch)},
                headers=headers
            )
            if r.status_code == 200:
                tracks.extend(r.json().get("albums", []))
            else:
                print(f"Spotify API Error: {r.text}")
        return tracks

    def get_app_token(self):
        auth_header = base64.b64encode(f"{settings.SPOTIFY_CLIENT_ID}:{settings.SPOTIFY_CLIENT_SECRET}".encode()).decode()
        headers = {"Authorization": f"Basic {auth_header}"}
        data = {"grant_type": "client_credentials"}
        r = requests.post("https://accounts.spotify.com/api/token", headers=headers, data=data)
        r.raise_for_status()
        return r.json()["access_token"]

    def get_current_user_profile(self):
        if not self.token:
            return None

        headers = {"Authorization": f"Bearer {self.token}"}

        response = requests.get("https://api.spotify.com/v1/me", headers=headers)
        if response.status_code == status.HTTP_200_OK:
            return response.json()
        return {"error": "Spotify API Error", "details": response.json()}

    def get_user_top_items(self, type_, time_range, limit=20, offset=0):
        if not self.token:
            return None

        headers = {"Authorization": f"Bearer {self.token}"}
        params = {
            "time_range": time_range,
            "limit": limit,
            "offset": offset
        }

        response = requests.get(
            f"https://api.spotify.com/v1/me/top/{type_}",
            headers=headers, params=params
        )
        if response.status_code == status.HTTP_200_OK:
            return response.json()
        return {"error": "Spotify API Error", "details": response.json()}

    def get_recently_played(self, limit, after=None, before=None):
        if not self.token:
            return None

        headers = {"Authorization": f"Bearer {self.token}"}
        params = {
            "limit": limit, "after": after, "before": before
        }

        response = requests.get(
            "https://api.spotify.com/v1/me/player/recently-played",
            headers=headers, params=params
        )
        if response.status_code == status.HTTP_200_OK:
            return response.json()
        return {"error": "Spotify API Error", "details": response.json()}

    def get_user_top_genres(self, time_range, limit=10):
        artists_data = self.get_user_top_items(
            type_="artists",
            time_range=time_range,
            limit=50
        )

        if not artists_data or "items" not in artists_data:
            return []

        all_genres = []
        for artist in artists_data["items"]:
            all_genres.extend(artist.get("genres", []))

        genre_counts = Counter(all_genres).most_common(limit)
        result = [
            {
                "name": genre,
                "count": count,
                "percent": round((count / len(artists_data['items'])) * 100)
            }
            for genre, count in genre_counts
        ]

        return result

    def get_user_token(self):
        try:
            token_obj = SocialToken.objects.get(
                account__user=self.user,
                account__provider='spotify'
            )
        except SocialToken.DoesNotExist:
            return None

        if token_obj.expires_at and token_obj.expires_at <= timezone.now() + timedelta(minutes=1):
            return self._refresh_user_token(token_obj)

        return token_obj.token

    def _refresh_user_token(self, token_obj):
        try:
            app = SocialApp.objects.get(provider="spotify")
        except SocialApp.DoesNotExist:
            raise Exception("Spotify SocialApp not configured")

        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': token_obj.token_secret,
            'client_id': app.client_id,
            'client_secret': app.secret,
        }

        response = requests.post('https://accounts.spotify.com/api/token', data=payload)

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            token_obj.token = data["access_token"]
            token_obj.expires_at = timezone.now() + timedelta(seconds=data.get('expires_in', 3600))

            if "refresh_token" in data:
                token_obj.token_secret = data["refresh_token"]

            token_obj.save()
            return token_obj.token
        else:
            return None
