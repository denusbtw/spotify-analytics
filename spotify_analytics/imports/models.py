from django.db import models
from django.conf import settings

from spotify_analytics.core.models import UUIDModel, TimestampedModel


class ImportJob(UUIDModel, TimestampedModel):
    class Status(models.TextChoices):
        UPLOADED = "uploaded", "Uploaded"
        PARSED = "parsed", "Parsed"
        FETCHING = "fetching", "Fetching"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="import_jobs"
    )

    source_file = models.FileField(upload_to="imports/")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UPLOADED
    )
    error = models.TextField(blank=True, default="")


# class ParsedSpotifyTrack(UUIDModel, TimestampedModel):
#     job = models.ForeignKey(
#         ImportJob,
#         on_delete=models.CASCADE,
#         related_name="parsed_spotify_items"
#     )
#
#     spotify_id = models.CharField(max_length=22)
