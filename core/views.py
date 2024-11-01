from django.contrib.auth.models import Group, Permission
from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .serializers import AddUsersToGroupSerializer, GroupSerializer, PermissionSerializer, AddUserToGroupSerializer, CreateGroupSerializer, UserSerializer, UpdateGroupSerializer
from .models import User

# Create your views here.


class GroupViewSet(viewsets.ModelViewSet):
    http_method_names = ['get', 'post', 'delete', 'put', 'options']
    queryset = Group.objects.prefetch_related('permissions').all()
    permission_classes = [permissions.IsAdminUser]

    def get_serializer_class(self):
        if self.action in ['add_user', 'remove_user']:
            return AddUserToGroupSerializer
        elif self.action == "add_users":
            return AddUsersToGroupSerializer
        elif self.request.method == "POST":
            return CreateGroupSerializer
        elif self.request.method == "PUT":
            return UpdateGroupSerializer
        return GroupSerializer

    @action(detail=True, methods=['post'])
    def add_user(self, request, pk=None):
        """Add a user to a group."""
        group = self.get_object()
        user_id = request.data.get('user_id')

        try:
            user = User.objects.get(id=user_id)
            group.user_set.add(user)
            return Response({"message": f"User {user.username} added to group {group.name}."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def add_users(self, request, pk=None):
        """Add multiple users to a group with a single bulk query."""
        group = self.get_object()
        user_ids = request.data.get('user_ids', [])

        if not isinstance(user_ids, list):
            return Response({"error": "user_ids must be a list of user IDs."}, status=status.HTTP_400_BAD_REQUEST)

        # Retrieve all users with the specified IDs in one query
        users = User.objects.filter(id__in=user_ids)
        found_user_ids = set(user.id for user in users)
        missing_user_ids = [
            user_id for user_id in user_ids if user_id not in found_user_ids]

        # Add the retrieved users to the group in one operation
        group.user_set.add(*users)

        response_data = {
            "message": f"Users added to group {group.name}.",
            "added_users": [user.username for user in users],
            "errors": [f"User with ID {user_id} not found." for user_id in missing_user_ids]
        }

        return Response(response_data, status=status.HTTP_200_OK if not missing_user_ids else status.HTTP_207_MULTI_STATUS)

    @action(detail=True, methods=['get'])
    def list_users(self, request, pk=None):
        """Retrieve the list of users in a group."""
        group = self.get_object()
        users = group.user_set.all()

        # Serialize the users
        serializer = UserSerializer(users, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def remove_user(self, request, pk=None):
        """Remove a user from a group."""
        group = self.get_object()
        user_id = request.data.get('user_id')

        try:
            user = User.objects.get(id=user_id)
            group.user_set.remove(user)
            return Response({"message": f"User {user.username} removed from group {group.name}."}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def remove_users(self, request, pk=None):
        """Remove multiple users from a group with a single bulk query."""
        group = self.get_object()
        user_ids = request.data.get('user_ids', [])

        if not isinstance(user_ids, list):
            return Response({"error": "user_ids must be a list of user IDs."}, status=status.HTTP_400_BAD_REQUEST)

        # Retrieve all users with the specified IDs in one query
        users = User.objects.filter(id__in=user_ids)
        found_user_ids = set(user.id for user in users)
        missing_user_ids = [
            user_id for user_id in user_ids if user_id not in found_user_ids]

        group.user_set.remove(*users)

        response_data = {
            "message": f"Users removed from group {group.name}.",
            "removed_users": [user.username for user in users],
            "errors": [f"User with ID {user_id} not found." for user_id in missing_user_ids]
        }

        # Use 207 status if some users were not found; otherwise, 200
        status_code = status.HTTP_200_OK if not missing_user_ids else status.HTTP_207_MULTI_STATUS
        return Response(response_data, status=status_code)


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Permission.objects.exclude(name__startswith="Can ")
    serializer_class = PermissionSerializer
