from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from .models import Image


def create_instance_with_images(model_class, validated_data):
    """
    Creates an instance of the given model class and associates images.

    :param model_class: The model class for the instance to be created.
    :param validated_data: The validated data for the model and images.
    :return: The created instance of the model class.
    """
    images_data = validated_data.pop('images', [])
    with transaction.atomic():
        instance = model_class.objects.create(**validated_data)
        content_type = ContentType.objects.get_for_model(model_class)

        for path in images_data:
            Image.objects.create(
                path=path,
                content_type=content_type,
                object_id=instance.id
            )

    return instance
