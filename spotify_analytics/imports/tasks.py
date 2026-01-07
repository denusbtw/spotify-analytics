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
                    ip_addr=row["ip_addr"],
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

    spotify_ids = list(
        set(
            parsed_listens
            .values_list("spotify_track_id", flat=True)
        )
    )

    # -------------------------------
    # 1. Забезпечуємо існування ВСІХ Track
    # -------------------------------

    existing_track_ids = set(
        Track.objects
        .filter(spotify_id__in=spotify_ids)
        .values_list("spotify_id", flat=True)
    )

    ids_to_fetch = [sid for sid in spotify_ids if sid not in existing_track_ids]

    tracks_data = {}
    if ids_to_fetch:
        BATCH_SIZE = 50
        MAX_WORKERS = 3

        batches = [
            ids_to_fetch[i:i + BATCH_SIZE]
            for i in range(0, len(ids_to_fetch), BATCH_SIZE)
        ]

        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(service.get_tracks, batch): batch
                for batch in batches
            }
            for future in as_completed(futures):
                result = future.result()
                for t in result:
                    if t:
                        tracks_data[t["id"]] = t

    # -------------------------------
    # 2. Артисти
    # -------------------------------

    artist_data = {}
    for t in tracks_data.values():
        for a in t["artists"]:
            artist_data[a["id"]] = a
        for a in t["album"]["artists"]:
            artist_data[a["id"]] = a

    existing_artist_ids = set(
        Artist.objects
        .filter(spotify_id__in=artist_data.keys())
        .values_list("spotify_id", flat=True)
    )

    Artist.objects.bulk_create(
        [
            Artist(
                spotify_id=a_id,
                name=a["name"],
                spotify_url=a["external_urls"]["spotify"],
            )
            for a_id, a in artist_data.items()
            if a_id not in existing_artist_ids
        ],
        ignore_conflicts=True
    )

    artist_objs = {
        a.spotify_id: a
        for a in Artist.objects.filter(spotify_id__in=artist_data.keys())
    }

    # -------------------------------
    # 3. Альбоми
    # -------------------------------

    album_data = {
        t["album"]["id"]: t["album"]
        for t in tracks_data.values()
    }

    existing_album_ids = set(
        Album.objects
        .filter(spotify_id__in=album_data.keys())
        .values_list("spotify_id", flat=True)
    )

    Album.objects.bulk_create(
        [
            Album(
                spotify_id=alb_id,
                name=alb["name"],
                spotify_url=alb["external_urls"]["spotify"],
                type=alb["album_type"],
                release_date=parse_date(alb["release_date"])
                if alb.get("release_date_precision") == "day"
                else None,
                image=alb["images"][0]["url"] if alb.get("images") else None,
            )
            for alb_id, alb in album_data.items()
            if alb_id not in existing_album_ids
        ],
        ignore_conflicts=True
    )

    album_objs = {
        a.spotify_id: a
        for a in Album.objects.filter(spotify_id__in=album_data.keys())
    }

    AlbumArtist = Album.artists.through
    AlbumArtist.objects.bulk_create(
        [
            AlbumArtist(
                album_id=album_objs[alb["id"]].id,
                artist_id=artist_objs[a["id"]].id,
            )
            for alb in album_data.values()
            for a in alb["artists"]
            if alb["id"] in album_objs and a["id"] in artist_objs
        ],
        ignore_conflicts=True
    )

    # -------------------------------
    # 4. Треки
    # -------------------------------

    Track.objects.bulk_create(
        [
            Track(
                spotify_id=t["id"],
                name=t["name"],
                duration_ms=t["duration_ms"],
                explicit=t["explicit"],
                popularity=t.get("popularity"),
                spotify_url=t["external_urls"]["spotify"],
                album=album_objs.get(t["album"]["id"]),
                release_date=parse_date(t["album"]["release_date"])
                if t["album"].get("release_date_precision") == "day"
                else None,
                image=(
                    album_objs[t["album"]["id"]].image
                    if t["album"]["id"] in album_objs
                    else None
                ),
            )
            for t in tracks_data.values()
        ],
        ignore_conflicts=True
    )

    track_objs = {
        t.spotify_id: t
        for t in Track.objects.filter(spotify_id__in=spotify_ids)
    }

    # -------------------------------
    # 5. Track ↔ Artist
    # -------------------------------

    TrackArtist = Track.artists.through
    TrackArtist.objects.bulk_create(
        [
            TrackArtist(
                track_id=track_objs[t["id"]].id,
                artist_id=artist_objs[a["id"]].id,
            )
            for t in tracks_data.values()
            for a in t["artists"]
            if t["id"] in track_objs and a["id"] in artist_objs
        ],
        ignore_conflicts=True
    )

    # -------------------------------
    # 6. ListeningHistory (ГОЛОВНЕ)
    # -------------------------------

    history = [
        ListeningHistory(
            user=import_job.user,
            track=track_objs[parsed.spotify_track_id],
            ip_addr=parsed.ip_addr,
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
        for parsed in parsed_listens
        if parsed.spotify_track_id in track_objs
    ]

    ListeningHistory.objects.bulk_create(history, batch_size=500)

    import_job.status = ImportJob.Status.COMPLETED
    import_job.save(update_fields=["status"])
