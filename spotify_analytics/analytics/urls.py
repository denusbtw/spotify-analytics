from django.urls import path

from spotify_analytics.analytics.views import PlatformStatsView, SkippedStatsView, ShuffleStatsView, ArtistShareView, \
    AnalyticsOverviewView

app_name = "analytics"
urlpatterns = [
    path("overview/", AnalyticsOverviewView.as_view(), name="overview"),
    path("platforms/", PlatformStatsView.as_view(), name="platforms"),
    path("skipped/", SkippedStatsView.as_view(), name="skipped"),
    path("shuffle/", ShuffleStatsView.as_view(), name="shuffle"),
    path("artist-share/", ArtistShareView.as_view(), name="artist_share"),
]