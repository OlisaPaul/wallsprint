from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework import status
from .models import File

def get_bulk_delete_serializer_class(model):
    class BulkDeleteSerializer(serializers.Serializer):
        ids = serializers.ListField(
            child=serializers.IntegerField(),
            allow_empty=False,
            help_text="A list of group IDs to delete."
        )

        def validate_ids(self, value):
            existing_ids = set(model.objects.filter(id__in=value).values_list('id', flat=True))
            missing_ids = set(value) - existing_ids
            if missing_ids:
                raise serializers.ValidationError(f"The following IDs are invalid: {list(missing_ids)}")
            return value
    
    return BulkDeleteSerializer


def bulk_delete_objects(request, model):
    serializer_class = get_bulk_delete_serializer_class(model)
    serializer = serializer_class(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    object_ids = serializer.validated_data['ids']
    
    objects_to_delete = model.objects.filter(id__in=object_ids)
    deleted_count, _ = objects_to_delete.delete()
    
    return Response(
        {"detail": f"Deleted {len(object_ids)} objects."},
        status=status.HTTP_204_NO_CONTENT
    )



def create_instance_with_files(model_class, validated_data):
    """
    Creates an instance of the given model class and associates images.

    :param model_class: The model class for the instance to be created.
    :param validated_data: The validated data for the model and images.
    :return: The created instance of the model class.
    """
    files_data = validated_data.pop('files', [])

    with transaction.atomic():
        instance = model_class.objects.create(**validated_data)
        content_type = ContentType.objects.get_for_model(model_class)

        for path in files_data:
            File.objects.create(
                path=path,
                content_type=content_type,
                object_id=instance.id
            )

    return instance


def get_queryset_for_models_with_files(model_class):

    content_type = ContentType.objects.get_for_model(model_class)

    return model_class.objects.prefetch_related(
        models.Prefetch(
            'files',
            queryset=File.objects.filter(content_type=content_type)
        )
    )
