from django.db import models
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework import status
from cloudinary.uploader import upload
from cloudinary.api import resource
from cloudinary.exceptions import Error
from .models import File, Cart, CatalogItem, CartItem
from django.http import HttpRequest

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

        for file in files_data:
            file_size = None
            cloudinary_path = None

            if isinstance(file, InMemoryUploadedFile):
                file_size = file.size
                try:
                    upload_result = upload(file)
                    cloudinary_path = upload_result.get("public_id")
                except Error as e:
                    print(f"Error uploading file {file}: {e}")
                    continue
            else:
                try:
                    file_metadata = resource(file)
                    file_size = file_metadata.get("bytes")
                    cloudinary_path = file
                except Error as e:
                    print(f"Error fetching metadata for {file}: {e}")
                    continue

            File.objects.create(
                path=cloudinary_path,
                file_size=file_size,
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


class CustomModelViewSet(ModelViewSet):
    """
    A custom ModelViewSet that adds a bulk delete endpoint.
    """
    @action(detail=False, methods=['delete'], url_path='delete-multiple')
    def bulk_delete(self, request, *args, **kwargs):
        """
        Delete multiple objects by providing a list of IDs.
        """
        ids = request.data.get('ids', [])
        if not isinstance(ids, list) or not ids:
            return Response(
                {"detail": "Invalid input. Provide a list of IDs to delete."},
                status=status.HTTP_400_BAD_REQUEST
            )

        queryset = self.filter_queryset(self.get_queryset())

        # Filter objects to be deleted
        objects_to_delete = queryset.filter(id__in=ids)
        count = objects_to_delete.count()

        if count == 0:
            return Response(
                {"detail": "No matching objects found for the provided IDs."},
                status=status.HTTP_404_NOT_FOUND
            )

        objects_to_delete.delete()

        return Response(
            {"detail": f"Successfully deleted {count} object(s)."},
            status=status.HTTP_200_OK
        )

def get_base_url(request: HttpRequest) -> str:
    scheme = request.scheme
    host = request.get_host()  
    return f"{scheme}://{host}"

def validate_catalog_item_id(value):
        if not CatalogItem.objects.filter(pk=value).exists():
            raise serializers.ValidationError(
                "No catalog_item with the given ID")
        return value

def validate_catalog(context, attrs, model_class, field_name, instance=None):
    catalog_item = instance.catalog_item if instance else attrs.get('catalog_item')
    quantity = attrs.get('quantity')
    cart_id = context[f"{field_name}_id"]
    

    if  not model_class.objects.filter(pk=cart_id).exists():
        raise serializers.ValidationError(f"No {field_name} with the given ID")

    # if not catalog_item.can_item_be_ordered:
    #     raise serializers.ValidationError(
    #         f"{catalog_item.title} cannot be ordered.")

    pricing_grid = catalog_item.pricing_grid
    if quantity > catalog_item.available_inventory:
        raise serializers.ValidationError(
            {"quantity": f"The quantity of {catalog_item.title} in the cart is more than the available inventory."}
        )

    if not isinstance(pricing_grid, list):
        raise serializers.ValidationError(
            "No pricing grid for this catalog item"
        )
    if not any(entry["minimum_quantity"] == quantity for entry in pricing_grid):
        raise serializers.ValidationError(
            {"quantity": "The quantity provided is not in the pricing grid."}
        )
    return attrs

def save_item(context, validated_data, model_class, field_name, old_instance):
    id = context[field_name]
    catalog_item = old_instance.catalog_item if old_instance else validated_data.get('catalog_item')
    quantity = validated_data['quantity']

    pricing_grid = catalog_item.pricing_grid
    item = next(
        (entry for entry in pricing_grid if entry["minimum_quantity"] == quantity), None)
    unit_price = item['unit_price']
    sub_total = item['minimum_quantity'] * unit_price
    validated_data['sub_total'] = sub_total

    if old_instance:
        old_instance.unit_price = unit_price
        old_instance.sub_total = sub_total
        old_instance.quantity = quantity
        old_instance.save()

        return old_instance

    
    instance = model_class.objects.create(
        **({field_name: id}),
        unit_price=unit_price,
        **validated_data)

    return instance