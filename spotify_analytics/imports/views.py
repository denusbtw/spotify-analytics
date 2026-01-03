from rest_framework import views, permissions, response, status, generics

from .models import ImportJob
from .serializers import MultipleFileUploadSerializer


class MultipleFileUploadView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MultipleFileUploadSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        files = serializer.validated_data["files"]

        created_jobs = []

        for f in files:
            import_job = ImportJob.objects.create(
                user=request.user,
                source_file=f,
                status=ImportJob.Status.UPLOADED
            )
            created_jobs.append(import_job.id)

        return response.Response(
            {"import_job_ids": created_jobs},
            status=status.HTTP_201_CREATED
        )
