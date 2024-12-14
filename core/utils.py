from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework import status
from .models import User

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

def generate_jwt_for_user(user_id):
    """
    Generate a JWT token pair (access and refresh) for a given user.
    """
    try:

        user = User.objects.get(pk=user_id)
        

        refresh = RefreshToken.for_user(user)
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }
    except User.DoesNotExist:
        raise ValueError("User does not exist")

