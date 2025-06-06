import re
import os
import random
import secrets
import string
from typing import Dict
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.db import transaction
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.models import Permission, Group
from djoser.serializers import UserSerializer as BaseUserSerializer, UserCreateSerializer as BaseUserCreateSerializer, UserDeleteSerializer
from rest_framework.exceptions import AuthenticationFailed
from djoser.conf import settings
from djoser.serializers import TokenCreateSerializer, SendEmailResetSerializer
from djoser.compat import get_user_email, get_user_email_field_name
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from dotenv import load_dotenv
from .signals import group_created
from .models import User, StaffNotification, BlacklistedToken
from .utils import generate_jwt_for_user, blacklist_token
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync


load_dotenv()


def send_email(user: User, context, subject, template):
    message = render_to_string(template, context)
    send_mail(
        subject,
        message,
        os.getenv('EMAIL_HOST_USER'),
        [user.email],
        fail_silently=False,
        html_message=message
    )


def generate_random_password(length=12):
    characters = string.ascii_letters + string.digits + string.punctuation
    password = ''.join(secrets.choice(characters) for _ in range(length))
    return password


class CustomUserDeleteSerializer(UserDeleteSerializer):
    current_password = serializers.CharField(
        style={"input_type": "password"}, required=False)


class SimpleGroupSerializer(ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']


class UpdateCurrentUserSerializer(BaseUserSerializer):
    groups_count = serializers.SerializerMethodField()
    groups = SimpleGroupSerializer(many=True, read_only=True)
    permissions = serializers.SerializerMethodField()
    is_superuser = serializers.SerializerMethodField()

    class Meta(BaseUserSerializer.Meta):
        fields = ['id', 'email', 'name', 'username', 'is_active', 'status',
                  'is_staff', 'is_superuser', 'groups',  "groups_count", 'permissions']
        read_only_fields = (settings.LOGIN_FIELD, 'email', 'is_active', 'status',
                            'is_staff', 'is_superuser', 'groups', "groups_count", 'permissions')

    def get_groups_count(self, obj):
        return obj.groups.count()

    def get_is_superuser(self, obj: User):
        return obj.is_superuser or obj.groups.filter(extendedgroup__for_superuser=True).exists()

    def get_permissions(self, obj):
        """
        Return a list of all permissions assigned to the user, either
        directly or through groups.
        """
        permissions = set()

        permissions.update(obj.user_permissions.all())

        for group in obj.groups.all():
            permissions.update(group.permissions.all())

        return [perm.name for perm in permissions]


class AcceptInvitationSerializer(BaseUserSerializer):
    password = serializers.CharField(write_only=True)

    class Meta(BaseUserSerializer.Meta):
        fields = ['name', 'password']

    def validate(self, attrs):
        request = self.context['request']
        user = User.objects.get(pk=request.user.id)

        blacklist_token(request)

        if user.username:
            raise serializers.ValidationError('Invitation already accepted')

        return attrs

    @transaction.atomic()
    def update(self, instance, validated_data):
        password = validated_data.get('password')
        user = super().update(instance, validated_data)

        if password:
            user.set_password(password)
            user.username = user.email
            user.save()

        return user


def _notify_permission_change(users):
    """Helper function to send permission updates for users"""
    channel_layer = get_channel_layer()
    permissions_updates = [
        {
            "user_id": user.id,
            "permissions": [perm.name for perm in Permission.objects.filter(codename__in=[perm.split('.')[1] for perm in user.get_all_permissions()])]
        }
        for user in users
    ]

    async_to_sync(channel_layer.group_send)(
        "staff_permissions",
        {
            "type": "bulk_permissions_update",
            "updates": permissions_updates
        }
    )


class UserSerializer(BaseUserSerializer):
    groups_count = serializers.SerializerMethodField()
    group_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    groups = SimpleGroupSerializer(many=True, read_only=True)
    permissions = serializers.SerializerMethodField()
    is_superuser = serializers.SerializerMethodField()

    class Meta(BaseUserSerializer.Meta):
        fields = ['id', 'email', 'name', 'username', 'is_active', 'status',
                  'is_staff', 'is_superuser', 'groups', "group_ids", "groups_count", 'permissions']
        read_only_fields = (settings.LOGIN_FIELD, 'email',
                            'is_staff', 'is_superuser', 'groups', 'username', 'status')

    def validate(self, attrs):
        self.group_ids = attrs.pop('group_ids', [])
        return super().validate(attrs)

    def get_is_superuser(self, obj: User):
        return obj.is_superuser or obj.groups.filter(extendedgroup__for_superuser=True).exists()

    def get_permissions(self, obj):
        """
        Return a list of all permissions assigned to the user, either
        directly or through groups.
        """
        permissions = set()

        permissions.update(obj.user_permissions.all())

        for group in obj.groups.all():
            permissions.update(group.permissions.all())

        return [perm.name for perm in permissions]

    @transaction.atomic()
    def update(self, instance, validated_data):
        email_field = get_user_email_field_name(User)
        instance.email_changed = False
        if settings.SEND_ACTIVATION_EMAIL and email_field in validated_data:
            instance_email = get_user_email(instance)
            if instance_email != validated_data[email_field]:
                instance.is_active = False
                instance.email_changed = True
                instance.save(update_fields=["is_active"])

        user = super().update(instance, validated_data)

        if hasattr(self, 'group_ids') and not user.is_superuser:
            groups = Group.objects.filter(id__in=self.group_ids)
            user.groups.set(groups)
            # Send WebSocket notification when groups are updated
            _notify_permission_change([user])

        return user

    def get_groups_count(self, obj):
        return obj.groups.count()


class PermissionSerializer(ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename', 'content_type']


class GroupSerializer(ModelSerializer):
    permissions = PermissionSerializer(many=True)
    users = serializers.SerializerMethodField(method_name='get_users')
    date_created = serializers.DateTimeField(
        source='extendedgroup.date_created', read_only=True)
    for_superuser = serializers.BooleanField(
        source='extendedgroup.for_superuser', read_only=True)

    class Meta:
        model = Group
        fields = ['id', 'name', 'permissions',
                  'users', 'date_created', 'for_superuser']

    def get_users(self, obj):
        users = obj.user_set.all()
        return UserSerializer(users, many=True).data


class UserCreateSerializer(BaseUserCreateSerializer):
    group_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )

    class Meta(BaseUserCreateSerializer.Meta):
        fields = ['id', 'email', 'password', 'username', 'name', 'group_ids']

    def validate(self, attrs):
        self.group_ids = attrs.pop('group_ids', [])
        return super().validate(attrs)
    
    def validate_email(self, value):
        return value.lower()

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Username already exists.")

        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "Username cannot be an email that already exists.")

        return value

    def validate_password(self, value):
        validate_password(value)

        name = self.initial_data.get('name', '').lower()
        if name and name in value.lower():
            raise serializers.ValidationError(
                "Password cannot contain your name.")

        return value

    @transaction.atomic()
    def create(self, validated_data):
        validated_data = {**validated_data,
                          'is_staff': True, 'status': 'active'}
        user = super().create(validated_data)
        subject = "Welcome to Walls Printing!"
        template = "email/welcome_email.html"
        temporary_password = validated_data.get(
            "password")
        context = {
            "user": user,
            "temporary_password": temporary_password,
            "login_url": os.getenv('STAFF_LOGIN_URL')
        }

        # send_email(user=user, context=context,
        #            subject=subject, template=template)

        if self.group_ids:
            groups = Group.objects.filter(id__in=self.group_ids)
            user.groups.add(*groups)

        return user


class InviteStaffSerializer(BaseUserCreateSerializer):
    class Meta(BaseUserCreateSerializer.Meta):
        fields = ['email', 'groups']

    def validate(self, attrs):
        temporary_password = generate_random_password()
        attrs['password'] = temporary_password
        self.password = temporary_password
        self.groups = attrs.pop('groups', [])
        return super().validate(attrs)

    @transaction.atomic()
    def create(self, validated_data):
        request = self.context['request']
        inviter = User.objects.get(pk=request.user.id)
        validated_data = {**validated_data, 'is_staff': True}
        user = super().create(validated_data)
        token_dict = generate_jwt_for_user(user.id)
        token = token_dict['access']

        subject = "Invitation to Join the Walls Printing Team"
        context = {
            "inviter_email": inviter.email,
            "inviter_name": inviter.name,
            "invitation_link": f'{os.getenv("CLIENT_INVITATION_URL")}{token}'
        }
        template = 'email/invitation_email.html'

        if self.groups:
            user.groups.add(*self.groups)

        send_email(user=user, context=context,
                   subject=subject, template=template)

        return user


class ResendStaffInvitationSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
            if user.username:
                raise serializers.ValidationError(
                    "Invitation already accepted")
        except User.DoesNotExist:
            raise serializers.ValidationError("No existing user with email")

        return value


class UserListSerializer(serializers.ModelSerializer):
    is_in_group = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'is_in_group']

    def get_is_in_group(self, obj):
        group_id = self.context.get('group_id')
        return obj.groups.filter(id=group_id).exists() if group_id else False


class UpdateStaffSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['name', 'username', "status"]

    def update(self, instance, validated_data):
        validated_data['is_staff'] = True

        if validated_data['status']:
            is_active = not (validated_data['status'] == 'inactive')
            validated_data = {**validated_data, 'is_active': is_active}

        user = super().update(instance, validated_data)

        return user


class CreateGroupSerializer(ModelSerializer):
    user_ids = serializers.PrimaryKeyRelatedField(
        source='user_set',
        queryset=User.objects.all(),
        many=True
    )

    class Meta:
        model = Group
        fields = ['id', 'name', 'permissions', 'user_ids']

    def validate_name(self, attrs):
        name = attrs.lower()

        cleaned_name = re.sub(r'[^a-z0-9]', '', name)

        if "primaryadministrator" in cleaned_name:
            raise serializers.ValidationError(
                "Group name cannot contain the reserved word 'Primary Administrator'."
            )

        if Group.objects.filter(name__iexact=name).exists():
            raise serializers.ValidationError("Group name already exists")
        return attrs


class UpdateGroupSerializer(ModelSerializer):
    users = serializers.PrimaryKeyRelatedField(
        source='user_set',
        queryset=User.objects.all(),
        many=True
    )

    def validate(self, attrs):
        name = attrs.get('name')
        instance = self.instance

        cleaned_name = re.sub(r'[^a-z0-9]', '', name)
        superuser_group = self.instance.extendedgroup.for_superuser

        if "primaryadministrator" in cleaned_name:
            if not superuser_group:
                raise serializers.ValidationError(
                    {"name": "Group name cannot contain the reserved word 'Primary Administrator'."}
                )
        elif superuser_group and name != instance.name:
            raise serializers.ValidationError(
                {'name': "You can not change the name of the default group"})

        return super().validate(attrs)

    class Meta:
        model = Group
        fields = ['name', 'permissions', 'users']

    # def validate_name(self, attrs):
    #     name = attrs.lower()
    #     if Group.objects.filter(name__iexact=name).exists():
    #         raise serializers.ValidationError("Group name already exists")
    #     return attrs


class AddUserToGroupSerializer(ModelSerializer):
    user_id = serializers.IntegerField()

    class Meta:
        model = Group
        fields = ['user_id']


class AddUsersToGroupSerializer(ModelSerializer):
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Group
        fields = ['user_ids']


class CustomTokenCreateSerializer(TokenCreateSerializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email:
            email = attrs["email"].lower()

        if email and password:
            user = authenticate(request=self.context.get('request'),
                                email=email, password=password)
            if not user:
                raise serializers.ValidationError('Invalid login credentials')
        else:
            raise serializers.ValidationError(
                'Must include "email" and "password".')

        attrs['user'] = user
        return attrs


class GenerateTokenSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(
        required=True, help_text="ID of the user to generate a token for")


class SimpleStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'email']


class StaffNotificationSerializer(serializers.ModelSerializer):
    user = SimpleStaffSerializer()

    class Meta:
        model = StaffNotification
        fields = ['id', 'user']


class CreateStaffNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffNotification
        fields = ['user']

    def validate_user(self, value):
        if not value.is_staff:
            raise serializers.ValidationError("User must be a staff member.")
        return value


class CustomObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        username = attrs.get(self.username_field)
        password = attrs.get("password")
        attrs[self.username_field] = username.lower() if username else None

        # Fetch the user manually
        user = User.objects.filter(**{self.username_field: username}).first()

        if user:
            if not user.is_active:
                raise AuthenticationFailed(
                    "Your account is inactive. Please contact support.")

        # Authenticate the user (case-insensitive username)
        user = authenticate(
            **{self.username_field: username.lower(), "password": password}
        )

        if not user:
            raise AuthenticationFailed(
                "Invalid email or password. Please try again.")

        return super().validate(attrs)


class CustomSendEmailResetSerializer(SendEmailResetSerializer):
    def validate(self, attrs):
        email = attrs.get('email')
        user = User.objects.filter(email__iexact=email).first()
        if not user.is_active:
            raise serializers.ValidationError(
                {'email': 'This account is inactive. Please contact support.'})
        return super().validate(attrs)
