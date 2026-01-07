import json
from rest_framework import serializers

class MultipleFileUploadSerializer(serializers.Serializer):
    files = serializers.ListField(
        child=serializers.FileField(),
        allow_empty=False
    )

    def validate_files(self, files):
        for f in files:
            # if f.size > 13 * 1024 * 1024: # 13 MB
            #     raise serializers.ValidationError(
            #         f"{f.name} перевищує ліміт."
            #     )

            try:
                f.seek(0)
                json.load(f)
                f.seek(0)
            except Exception:
                raise serializers.ValidationError(
                    f"{f.name} невалідний JSON"
                )

        return files
