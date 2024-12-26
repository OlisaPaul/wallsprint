import hashlib
from django.http import JsonResponse
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework import status
from .models import User, BlacklistedToken
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action


def get_bulk_delete_serializer_class(model):
    class BulkDeleteSerializer(serializers.Serializer):
        ids = serializers.ListField(
            child=serializers.IntegerField(),
            allow_empty=False,
            help_text="A list of group IDs to delete."
        )

        def validate_ids(self, value):
            existing_ids = set(model.objects.filter(
                id__in=value).values_list('id', flat=True))
            missing_ids = set(value) - existing_ids
            if missing_ids:
                raise serializers.ValidationError(
                    f"The following IDs are invalid: {list(missing_ids)}")
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


def generate_jwt_for_user(user_id):
    """
    Generate a JWT token pair (access and refresh) for a given user.
    """
    user = User.objects.get(pk=user_id)
    refresh = RefreshToken.for_user(user)
    return {
        'access': str(refresh.access_token),
        'refresh': str(refresh),
    }


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


def blacklist_token(request):
    def hash_token(token):
        return hashlib.sha256(token.encode()).hexdigest()

    auth_header = request.headers.get('Authorization')
    token = auth_header.split(' ')[1]
    hashed_token = hash_token(token)
    BlacklistedToken.objects.create(token_hash=hashed_token)
