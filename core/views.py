from django.contrib.auth.models import Group, Permission
from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .serializers import GroupSerializer, PermissionSerializer, AddGroupSerializer
from cuser.models import CUser

# Create your views here.


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAdminUser]

    @action(detail=True, methods=['post'], serializer_class=AddGroupSerializer)
    def add_user(self, request, pk=None):
        """Add a user to a group."""
        group = self.get_object()
        user_id = request.data.get('user_id')
        
        try:
            user = CUser.objects.get(id=user_id)
            group.user_set.add(user)
            return Response({"message": f"User {user.username} added to group {group.name}."}, status=status.HTTP_200_OK)
        except CUser.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], url_path='remove-user')
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


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer