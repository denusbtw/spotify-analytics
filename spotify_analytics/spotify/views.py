from allauth.socialaccount.providers.spotify.views import SpotifyOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView
from rest_framework import views, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from spotify_analytics.core.clients import CustomOauth2Client
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


class UserTopItemsView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, type_):
        spotify = SpotifyService(request.user)

        time_range = request.query_params.get("time_range", "medium_term")
        limit = request.query_params.get("limit", 10)
        offset = request.query_params.get("offset", 0)

        data = spotify.get_user_top_items(type_=type_, time_range=time_range, limit=limit, offset=offset)
        if not data:
            return Response({"error": "Spotify API Error"}, status=status.HTTP_400_BAD_REQUEST)

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
