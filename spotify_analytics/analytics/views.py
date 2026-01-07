from django.db.models import Count, Sum
from rest_framework import views, permissions, response

from spotify_analytics.core.models import ListeningHistory


class PlatformStatsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = (
            ListeningHistory.objects
            .filter(user=request.user)
            .values("platform")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        return response.Response(qs)


class SkippedStatsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = (
            ListeningHistory.objects
            .filter(user=request.user)
            .values("skipped")
            .annotate(count=Count("id"))
        )
        return response.Response(qs)


class ShuffleStatsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = (
            ListeningHistory.objects
            .filter(user=request.user)
            .values("shuffle")
            .annotate(count=Count("id"))
        )
        return response.Response(qs)


class ArtistShareView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = (
            ListeningHistory.objects
            .filter(user=request.user)
            .values("track__artists__name")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        top = qs[:5]
        other = sum(x["count"] for x in qs[5:])

        data = list(top)
        if other:
            data.append({"track__artists__name": "Other", "count": other})

        return response.Response(data)


class AnalyticsOverviewView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        queryset = ListeningHistory.objects.filter(user=user)

        metrics = queryset.aggregate(
            total_streams=Count('id'),
            total_ms=Sum('ms_played')
        )

        total_ms = metrics['total_ms'] or 0
        total_minutes = total_ms // 60000

        return response.Response({
            "total_streams": metrics['total_streams'] or 0,
            "minutes_streamed": total_minutes,
            "hours_streamed": total_minutes // 60,
            "different_tracks": queryset.values('track_id').distinct().count(),
            "different_artists": queryset.values('track__artists_id').distinct().count(),
            "different_albums": queryset.values('track__album_id').distinct().count(),
        })
