from django.contrib.gis.geoip2 import GeoIP2
from django.db.models import Count, Sum
from django.db.models.functions import ExtractHour
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

        base_metrics = queryset.aggregate(
            total_streams=Count('id'),
            total_ms=Sum('ms_played')
        )

        diff_tracks = queryset.values('track_id').distinct().count()
        diff_albums = queryset.values('track__album_id').distinct().count()
        diff_artists = queryset.values('track__artists').distinct().count()

        ms_in_minute = 1000 * 60
        minutes_in_hour = 60

        total_ms = base_metrics['total_ms'] or 0
        total_minutes = total_ms // ms_in_minute

        return response.Response({
            "total_streams": base_metrics['total_streams'],
            "minutes_streamed": total_minutes,
            "hours_streamed": total_minutes // minutes_in_hour,
            "different_tracks": diff_tracks,
            "different_artists": diff_artists,
            "different_albums": diff_albums,
        })


class ListeningActivityByHourView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        stats = (
            ListeningHistory.objects
            .filter(user=request.user)
            .annotate(hour=ExtractHour('played_at'))
            .values('hour')
            .annotate(
                streams=Count('id'),
                minutes=Sum('ms_played') / 60000
            )
            .order_by('hour')
        )

        hour_map = {h: {"hour": h, "streams": 0, "minutes": 0} for h in range(24)}
        for s in stats:
            hour_map[s['hour']] = {
                "hour": s['hour'],
                "streams": s['streams'],
                "minutes": round(s['minutes'] or 0)
            }

        return response.Response(hour_map.values())


class GeoStatsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        queryset = ListeningHistory.objects.filter(user=user)

        ip_stats = (
            queryset.values('ip_addr')
            .annotate(
                ms_played=Sum('ms_played'),
                sessions=Count('id')
            )
        )

        g = GeoIP2()
        city_groups = {}

        for entry in ip_stats:
            ip = entry['ip_addr']
            try:
                location = g.city(ip)
                city_key = f"{location['city']}_{location['country_code']}"

                if city_key not in city_groups:
                    city_groups[city_key] = {
                        'city': location['city'],
                        'country': location['country_code'],
                        'latitude': location['latitude'],
                        'longitude': location['longitude'],
                        'ms_played': 0,
                        'sessions': 0
                    }

                city_groups[city_key]['ms_played'] += entry['ms_played']
                city_groups[city_key]['sessions'] += entry['sessions']
            except Exception:
                continue

        return response.Response(list(city_groups.values()))
