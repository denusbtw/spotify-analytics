from django.urls import path

from spotify_analytics.analytics.views import PlatformStatsView, SkippedStatsView, ShuffleStatsView, ArtistShareView, \
    AnalyticsOverviewView, ListeningActivityByHourView, GeoStatsView

app_name = "analytics"
urlpatterns = [
    path("overview/", AnalyticsOverviewView.as_view(), name="overview"),
    path("platforms/", PlatformStatsView.as_view(), name="platforms"),
    path("skipped/", SkippedStatsView.as_view(), name="skipped"),
    path("shuffle/", ShuffleStatsView.as_view(), name="shuffle"),
    path("artist-share/", ArtistShareView.as_view(), name="artist_share"),
    path("activity-by-hour/", ListeningActivityByHourView.as_view(), name="listening_activity_by_hour"),
    path("geo/", GeoStatsView.as_view(), name="geo"),
]