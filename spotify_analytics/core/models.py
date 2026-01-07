import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(blank=True, default=timezone.now)
    updated_at = models.DateTimeField(blank=True, default=timezone.now)

    class Meta:
        abstract = True


class Artist(UUIDModel, TimestampedModel):
    name = models.CharField(max_length=255)
    image = models.URLField(blank=True, null=True)
    popularity = models.SmallIntegerField(null=True, blank=True)
    followers = models.IntegerField(null=True, blank=True)
    spotify_id = models.CharField(max_length=22, unique=True)
    spotify_url = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Album(UUIDModel, TimestampedModel):
    name = models.CharField(max_length=255)
    image = models.URLField(blank=True, null=True)
    type = models.CharField(max_length=50)
    release_date = models.DateField(null=True, blank=True)
    popularity = models.SmallIntegerField(null=True, blank=True)
    spotify_id = models.CharField(max_length=22, unique=True)
    spotify_url = models.CharField(max_length=255)

    artists = models.ManyToManyField(Artist, related_name="albums")

    def __str__(self):
        return self.name


class Track(UUIDModel, TimestampedModel):
    name = models.CharField(max_length=255)
    image = models.URLField(blank=True, null=True)
    duration_ms = models.BigIntegerField(null=True, blank=True)
    explicit = models.BooleanField(default=False)
    popularity = models.SmallIntegerField(null=True, blank=True)
    release_date = models.DateField(null=True, blank=True)
    spotify_id = models.CharField(max_length=22, unique=True)
    spotify_url = models.CharField(max_length=255)

    album = models.ForeignKey(
        Album,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="tracks"
    )
    artists = models.ManyToManyField(Artist, related_name="tracks")

    def __str__(self):
        return self.name


class ListeningHistory(UUIDModel, TimestampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    ip_addr = models.GenericIPAddressField()
    played_at = models.DateTimeField()
    platform = models.CharField(max_length=20)
    ms_played = models.PositiveIntegerField()
    spotify_track_id = models.CharField(max_length=22)
    reason_start = models.CharField(max_length=20)
    reason_end = models.CharField(max_length=20)
    shuffle = models.BooleanField()
    skipped = models.BooleanField()
    offline = models.BooleanField(null=True)
    offline_timestamp = models.PositiveBigIntegerField(null=True)
