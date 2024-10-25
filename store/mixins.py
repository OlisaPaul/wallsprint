from django.db import transaction
from rest_framework.response import Response
from rest_framework import status
from .models import File


class HandleImagesMixin:
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            instance = serializer.save()

            images_data = request.FILES.getlist('images')
            if images_data:
                for image_data in images_data:

                    File.objects.create(
                        file=image_data,
                        content_object=instance
                    )

            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
