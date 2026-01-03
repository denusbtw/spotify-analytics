from django.urls import path, include

from spotify_analytics.spotify.views import SpotifyLoginView


urlpatterns = [
    path("auth/spotify/", SpotifyLoginView.as_view(), name="spotify_login"),
    path("auth/", include("dj_rest_auth.urls")),
    path("spotify/", include("spotify_analytics.spotify.urls")),
    path("imports/", include("spotify_analytics.imports.urls")),
]