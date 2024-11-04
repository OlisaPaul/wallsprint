from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from .models import File


def create_instance_with_images(model_class, validated_data):
    """
    Creates an instance of the given model class and associates images.

    :param model_class: The model class for the instance to be created.
    :param validated_data: The validated data for the model and images.
    :return: The created instance of the model class.
    """
    images_data = validated_data.pop('files', [])
    reverse_relationship_data = validated_data.pop('quote_requests', None)  # Adjust field name accordingly
    
    with transaction.atomic():
        instance = model_class.objects.create(**validated_data)
        content_type = ContentType.objects.get_for_model(model_class)

        for path in images_data:
            File.objects.create(
                path=path,
                content_type=content_type,
                object_id=instance.id
            )

        if reverse_relationship_data:
            instance.quote_requests.set(reverse_relationship_data)  # Adjust field name accordingly

    return instance

def get_queryset_for_models_with_files(model_class):
   
    content_type = ContentType.objects.get_for_model(model_class)

    return model_class.objects.prefetch_related(
        models.Prefetch(
            'files',
            queryset=File.objects.filter(content_type=content_type)
        )
    )