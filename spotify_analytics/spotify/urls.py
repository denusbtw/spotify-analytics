from django.urls import path

from spotify_analytics.spotify.views import CurrentUserProfileView, UserTopItemsView, UserRecentlyPlayedView, \
    UserTopGenresView

app_name = "spotify"
urlpatterns = [
    path("me/", CurrentUserProfileView.as_view(), name="me"),
    path("top/genres/", UserTopGenresView.as_view(), name="top_genres"),
    path("top/<str:type_>/", UserTopItemsView.as_view(), name="top_items"),
    path("recently-played/", UserRecentlyPlayedView.as_view(), name="recently_played"),
]