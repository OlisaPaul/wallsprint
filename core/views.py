import os
from django.db.models import Count
from rest_framework.permissions import AllowAny,  IsAuthenticated, IsAdminUser
from django.contrib.auth.models import Group, Permission
from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework import mixins
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from dotenv import load_dotenv
from .serializers import (AddUsersToGroupSerializer, GroupSerializer, PermissionSerializer, AddUserToGroupSerializer, CreateGroupSerializer,
                          UserListSerializer, UserSerializer, UpdateGroupSerializer, UserCreateSerializer, InviteStaffSerializer, UpdateStaffSerializer,
                          UpdateCurrentUserSerializer, AcceptInvitationSerializer, ResendStaffInvitationSerializer, send_email
                          )
from .models import User
from .utils import bulk_delete_objects, generate_jwt_for_user

load_dotenv()
# Create your views here.


class GroupViewSet(viewsets.ModelViewSet):
    http_method_names = ['get', 'post', 'delete', 'put', 'options']
    queryset = Group.objects.prefetch_related('permissions', 'user_set').all()
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

    @action(detail=False, methods=['delete'], url_path='delete-multiple')
    def delete_multiple(self, request):
        return bulk_delete_objects(request, Group)

    @action(detail=False, methods=['get'], url_path='with-users')
    def groups_with_users(self, request):
        """Retrieve groups that have at least one user assigned."""
        groups = self.queryset.annotate(
            user_count=Count('user')).filter(user_count__gt=0)
        serializer = self.get_serializer(groups, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='without-users')
    def groups_without_users(self, request):
        """Retrieve groups that have no users assigned."""
        groups = self.queryset.annotate(
            user_count=Count('user')).filter(user_count=0)
        serializer = self.get_serializer(groups, many=True)
        return Response(serializer.data)

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


class StaffViewSet(viewsets.ModelViewSet, viewsets.GenericViewSet):
    http_method_names = ['post', 'put', 'get', 'delete']
    queryset = User.objects.prefetch_related(
        'groups__permissions').filter(is_staff=True)
    serializer_class = InviteStaffSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_serializer_context(self):
        return {'request': self.request}

    def get_serializer_class(self):
        if self.action == 'invite_user':
            return InviteStaffSerializer
        if self.action == 'resend_invitation':
            return ResendStaffInvitationSerializer
        elif self.action == 'me':
            return UpdateCurrentUserSerializer
        elif self.action == 'accept_invitation':
            return AcceptInvitationSerializer
        elif self.request.method == 'POST':
            return UserCreateSerializer
        elif self.request.method == 'PUT':
            return UpdateStaffSerializer
        return UserSerializer

    @action(detail=False, methods=['delete'], url_path='delete-multiple')
    def delete_multiple(self, request):
        return bulk_delete_objects(request, User)

    @action(detail=False, methods=["GET", "PUT"])
    def me(self, request):
        user = User.objects.get(id=request.user.id)
        if request.method == "GET":
            serializer = UserSerializer(user)
            return Response(serializer.data)
        elif request.method == "PUT":
            serializer = UpdateCurrentUserSerializer(user, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        
    @action(detail=False, methods=["PUT",], url_path='accept-invitation')
    def accept_invitation(self, request):
        user = User.objects.get(id=request.user.id)
        serializer = AcceptInvitationSerializer(user, data=request.data, context={'request': self.request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    

    @action(detail=False, methods=['post'], url_path='invite-user')
    def invite_user(self, request):
        """Endpoint to send an invitation and assign groups to the user."""
        serializer = InviteStaffSerializer(data=request.data, context={'request': self.request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            {"message": f"Invitation sent to {user.email}."},
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['post'], url_path='resend-invitation')
    def resend_invitation(self, request):
        """Endpoint to resend invitation to a user."""
        context = {'request': self.request, 'resend': True}
        serializer = ResendStaffInvitationSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data.get('email')
        inviter = User.objects.get(pk=self.request.user.id)
        user = User.objects.get(email=email)
        token_dict = generate_jwt_for_user(user.id)
        token = token_dict['access']

        subject = "Invitation to Join the Walls Printing Team"
        context = {
            "inviter_email": inviter.email,
            "inviter_name": inviter.name,
            "invitation_link": f'{os.getenv("CLIENT_INVITATION_URL")}{token}'
        }
        template = 'email/invitation_email.html'

        send_email(user=user, context=context,
                   subject=subject, template=template)

        return Response(
            {"message": f"Invitation sent to {email}."},
            status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=['get'], url_path='with-groups')
    def users_with_groups(self, request):
        """Retrieve groups that have at least one user assigned."""
        groups = self.queryset.annotate(
            group_count=Count('groups')).filter(group_count__gt=0)
        serializer = self.get_serializer(groups, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='without-groups')
    def users_without_groups(self, request):
        """Retrieve groups that have at least one user assigned."""
        groups = self.queryset.annotate(
            group_count=Count('groups')).filter(group_count=0)
        serializer = self.get_serializer(groups, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='list-with-group-status')
    def list_with_group_status(self, request):
        """Endpoint to list users with their membership status for a specific group."""
        group_id = request.query_params.get('group_id')
        if not group_id:
            return Response({"error": "group_id is required as a query parameter."},
                            status=status.HTTP_400_BAD_REQUEST)

        serializer = UserListSerializer(
            self.queryset, many=True, context={'group_id': group_id})
        return Response(serializer.data, status=status.HTTP_200_OK)


class GenerateTokenForUser(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        user_id = request.data.get('user_id')
        token = generate_jwt_for_user(user_id)

        return Response(token)
