from allauth.socialaccount.providers.spotify.views import SpotifyOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView
from django.db.models import F
from django.db.models.aggregates import Count, Sum, Min, Max
from rest_framework import views, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from spotify_analytics.core.clients import CustomOauth2Client
from spotify_analytics.core.models import ListeningHistory
from spotify_analytics.spotify.services import SpotifyService


class SpotifyLoginView(SocialLoginView):
    adapter_class = SpotifyOAuth2Adapter
    client_class = CustomOauth2Client
    callback_url = "http://127.0.0.1:5173/spotify-callback/"


class CurrentUserProfileView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        spotify = SpotifyService(request.user)

        data = spotify.get_current_user_profile()
        if not data:
            return Response(
                {"error": "Failed to authenticate with Spotify"}, status=status.HTTP_401_UNAUTHORIZED
            )

        return Response(data)


class UserTopTracksView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        spotify = SpotifyService(request.user)
        time_range = request.query_params.get("time_range", "medium_term")
        limit = request.query_params.get("limit", 10)
        offset = request.query_params.get("offset", 0)

        data = spotify.get_top_tracks(time_range=time_range, limit=limit, offset=offset)
        if not data:
            return Response({"error": "Spotify API Error"}, status=status.HTTP_400_BAD_REQUEST)

        items = data["items"]
        spotify_ids = [item["id"] for item in items]

        stats_qs = (
            ListeningHistory.objects
            .filter(
                user=request.user,
                spotify_track_id__in=spotify_ids
            )
            .values("spotify_track_id")
            .annotate(
                plays=Count("id"),
                total_ms=Sum("ms_played"),
                first_listened_at=Min("played_at"),
                last_listened_at=Max("played_at"),
            )
        )

        stats_map = {
            s["spotify_track_id"]: s
            for s in stats_qs
        }

        ms_in_minute = 1000 * 60

        for item in items:
            db_info = stats_map.get(item["id"])

            if not db_info:
                item["play_count"] = 0
                item["total_minutes_listened"] = 0
                item["first_streamed_at"] = None
                item["last_streamed_at"] = None
                continue

            item["play_count"] = db_info["plays"]
            item["total_minutes_listened"] = round(
                (db_info["total_ms"] or 0) / ms_in_minute
            )

            item["first_streamed_at"] = db_info["first_listened_at"]
            item["last_streamed_at"] = db_info["last_listened_at"]

        return Response(data)


class UserTopArtistsView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        spotify = SpotifyService(request.user)

        time_range = request.query_params.get("time_range", "medium_term")
        limit = request.query_params.get("limit", 10)
        offset = request.query_params.get("offset", 0)

        data = spotify.get_top_artists(time_range=time_range, limit=limit, offset=offset)
        if not data:
            return Response({"error": "Spotify API Error"}, status=status.HTTP_400_BAD_REQUEST)

        items = data["items"]
        artist_ids = [item["id"] for item in items]

        stats_qs = (
            ListeningHistory.objects
            .filter(
                user=request.user,
                track__artists__spotify_id__in=artist_ids
            )
            .values(artist_spotify_id=F("track__artists__spotify_id"))
            .annotate(
                plays=Count("id"),
                total_ms=Sum("ms_played"),
                first_listened_at=Min("played_at"),
                last_listened_at=Max("played_at"),
            )
        )

        stats_map = {
            s["artist_spotify_id"]: s
            for s in stats_qs
        }

        ms_in_minute = 60000

        for item in items:
            db_info = stats_map.get(item["id"])

            if not db_info:
                item["play_count"] = 0
                item["total_minutes_listened"] = 0
                item["first_streamed_at"] = None
                item["last_streamed_at"] = None
                continue

            item["play_count"] = db_info["plays"]
            item["total_minutes_listened"] = round(
                (db_info["total_ms"] or 0) / ms_in_minute
            )
            item["first_streamed_at"] = db_info["first_listened_at"]
            item["last_streamed_at"] = db_info["last_listened_at"]

        return Response(data)


class UserRecentlyPlayedView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        spotify = SpotifyService(request.user)

        limit = request.query_params.get("limit", 20)
        after = request.query_params.get("after", None)
        before = request.query_params.get("before", None)

        data = spotify.get_recently_played(limit=limit, after=after, before=before)
        if not data:
            return Response({"error": "Spotify API Error"}, status=status.HTTP_400_BAD_REQUEST)

        return Response(data)


class UserTopGenresView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        spotify = SpotifyService(request.user)

        time_range = request.query_params.get("time_range", "long_term")

        data = spotify.get_user_top_genres(time_range)
        if not data:
            return Response({"error": "Spotify API Error"}, status=status.HTTP_400_BAD_REQUEST)

        return Response(data)
