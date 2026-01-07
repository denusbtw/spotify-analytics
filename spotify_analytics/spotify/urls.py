from django.urls import path

from spotify_analytics.spotify.views import (
    CurrentUserProfileView,
    UserTopArtistsView,
    UserRecentlyPlayedView,
    UserTopGenresView, UserTopTracksView
)

app_name = "spotify"
urlpatterns = [
    path("me/", CurrentUserProfileView.as_view(), name="me"),
    path("top/genres/", UserTopGenresView.as_view(), name="top_genres"),
    path("top/tracks/", UserTopTracksView.as_view(), name="top_tracks"),
    path("top/artists/", UserTopArtistsView.as_view(), name="top_artists"),
    path("recently-played/", UserRecentlyPlayedView.as_view(), name="recently_played"),
]