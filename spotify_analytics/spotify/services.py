from collections import Counter
from datetime import timedelta

import requests
from allauth.socialaccount.models import SocialToken, SocialApp
from django.utils import timezone
from rest_framework import status


class SpotifyService:
    def __init__(self, user):
        self.user = user
        self.token = self._get_token()

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

    def _get_token(self):
        try:
            token_obj = SocialToken.objects.get(
                account__user=self.user,
                account__provider='spotify'
            )
        except SocialToken.DoesNotExist:
            return None

        if token_obj.expires_at and token_obj.expires_at <= timezone.now() + timedelta(minutes=1):
            return self._refresh_token(token_obj)

        return token_obj.token

    def _refresh_token(self, token_obj):
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
