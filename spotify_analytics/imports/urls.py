from django.urls import path

from spotify_analytics.imports.views import MultipleFileUploadView

app_name = "imports"
urlpatterns = [
    path("", MultipleFileUploadView.as_view(), name="upload_files"),
]