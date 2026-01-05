import json
from concurrent.futures import ThreadPoolExecutor, as_completed

from celery import shared_task
from django.db import transaction
from django.utils.dateparse import parse_datetime, parse_date

from spotify_analytics.core.models import Artist, Album, Track, ListeningHistory
from spotify_analytics.imports.models import ImportJob, ParsedSpotifyListen
from spotify_analytics.spotify.services import SpotifyService


@shared_task(bind=True)
def parse_import_job_file(self, import_job_id):
    try:
        import_job = ImportJob.objects.get(id=import_job_id)
        with import_job.source_file.open("r") as f:
            data = json.load(f)

        listens_to_create = []
        for row in data:
            spotify_track_uri = row.get("spotify_track_uri")
            if not spotify_track_uri or not spotify_track_uri.startswith("spotify:track:"):
                continue

            listens_to_create.append(
                ParsedSpotifyListen(
                    import_job=import_job,
                    ts=parse_datetime(row["ts"]),
                    platform=row["platform"],
                    ms_played=row["ms_played"],
                    spotify_track_id=spotify_track_uri.split(":")[-1],
                    reason_start=row["reason_start"],
                    reason_end=row["reason_end"],
                    shuffle=row["shuffle"],
                    skipped=row["skipped"],
                    offline=row["offline"],
                    offline_timestamp=row["offline_timestamp"]
                )
            )

        with transaction.atomic():
            ParsedSpotifyListen.objects.bulk_create(listens_to_create, batch_size=500)
            import_spotify_tracks.delay(import_job_id)

        import_job.status = ImportJob.Status.PARSED
        import_job.save(update_fields=["status"])

    except Exception as e:
        import_job.status = ImportJob.Status.FAILED
        import_job.error = str(e)
        import_job.save(update_fields=["status", "error"])
        raise e


@shared_task(bind=True)
def import_spotify_tracks(self, import_job_id):
    import_job = ImportJob.objects.get(id=import_job_id)
    service = SpotifyService()

    parsed_listens = ParsedSpotifyListen.objects.filter(import_job=import_job)

    spotify_ids = list(parsed_listens.values_list("spotify_track_id", flat=True).distinct())

    existing_track_ids = set(Track.objects.filter(spotify_id__in=spotify_ids).values_list("spotify_id", flat=True))
    ids_to_fetch = [s for s in spotify_ids if s not in existing_track_ids]

    tracks_map = {}

    BATCH_SIZE = 50
    MAX_WORKERS = 3
    batch_size = 500

    batches = [ids_to_fetch[i:i + BATCH_SIZE] for i in range(0, len(ids_to_fetch), BATCH_SIZE)]
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(service.get_tracks, batch): batch for batch in batches}
        for future in as_completed(futures):
            for t in future.result():
                if t:
                    tracks_map[t["id"]] = t

    print("BULK CREATES")

    all_artist_ids = set(a["id"] for t in tracks_map.values() for a in t["artists"])
    existing_artists = Artist.objects.filter(spotify_id__in=all_artist_ids)
    existing_ids = set(existing_artists.values_list("spotify_id", flat=True))

    new_artists = [
        Artist(
            spotify_id=a["id"],
            name=a["name"],
            spotify_url=a["external_urls"]["spotify"]
        )
        for t in tracks_map.values()
        for a in t["artists"]
        if a["id"] not in existing_ids
    ]
    Artist.objects.bulk_create(new_artists, batch_size=batch_size, ignore_conflicts=True)
    artist_objs = {a.spotify_id: a for a in Artist.objects.filter(spotify_id__in=all_artist_ids)}

    all_album_ids = set(t["album"]["id"] for t in tracks_map.values())
    existing_albums = Album.objects.filter(spotify_id__in=all_album_ids)
    existing_album_ids = set(existing_albums.values_list("spotify_id", flat=True))

    new_albums = [
        Album(
            spotify_id=t["album"]["id"],
            name=t["album"]["name"],
            spotify_url=t["album"]["external_urls"]["spotify"],
            type=t["album"]["album_type"],
            release_date=parse_date(t["album"].get("release_date")),
            image=t["album"]["images"][0]["url"] if t["album"].get("images") else None
        )
        for t in tracks_map.values()
        if t["album"]["id"] not in existing_album_ids
    ]
    Album.objects.bulk_create(new_albums, batch_size=batch_size, ignore_conflicts=True)
    album_objs = {a.spotify_id: a for a in Album.objects.filter(spotify_id__in=all_album_ids)}

    tracks_to_create = []
    for t in tracks_map.values():
        album = album_objs.get(t["album"]["id"])
        tracks_to_create.append(
            Track(
                spotify_id=t["id"],
                name=t["name"],
                duration_ms=t["duration_ms"],
                explicit=t["explicit"],
                popularity=t.get("popularity"),
                spotify_url=t["external_urls"]["spotify"],
                release_date=parse_date(t["album"].get("release_date")),
                image=album.image if album else None,
                album=album
            )
        )
    Track.objects.bulk_create(tracks_to_create, batch_size=batch_size, ignore_conflicts=True)
    track_objs = {t.spotify_id: t for t in Track.objects.filter(spotify_id__in=tracks_map.keys())}

    history_to_create = []
    for parsed in parsed_listens:
        track = track_objs.get(parsed.spotify_track_id)
        if track:
            history_to_create.append(
                ListeningHistory(
                    user=parsed.import_job.user,
                    track=track,
                    played_at=parsed.ts,
                    platform=parsed.platform,
                    ms_played=parsed.ms_played,
                    spotify_track_id=parsed.spotify_track_id,
                    reason_start=parsed.reason_start,
                    reason_end=parsed.reason_end,
                    shuffle=parsed.shuffle,
                    skipped=parsed.skipped,
                    offline=parsed.offline,
                    offline_timestamp=parsed.offline_timestamp,
                )
            )
    ListeningHistory.objects.bulk_create(history_to_create, batch_size=batch_size)
