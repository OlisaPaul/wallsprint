import os
import secrets
import string
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.db import transaction
from django.contrib.auth.models import Group, Permission
from djoser.serializers import UserSerializer as BaseUserSerializer, UserCreateSerializer as BaseUserCreateSerializer, UserDeleteSerializer
from djoser.conf import settings
from djoser.serializers import TokenCreateSerializer
from djoser.compat import get_user_email, get_user_email_field_name
from dotenv import load_dotenv
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import User
from django.contrib.auth.hashers import make_password
import random

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


class UserSerializer(BaseUserSerializer):
    groups_count = serializers.SerializerMethodField()
    group_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    groups = SimpleGroupSerializer(many=True, read_only=True)

    class Meta(BaseUserSerializer.Meta):
        fields = ['id', 'email', 'name', 'username',
                  'is_staff', 'is_superuser', 'groups', "group_ids", "groups_count"]
        read_only_fields = (settings.LOGIN_FIELD, 'email',
                            'is_staff', 'is_superuser', 'groups', 'username')

    def validate(self, attrs):
        self.group_ids = attrs.pop('group_ids', [])
        return super().validate(attrs)

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

    class Meta:
        model = Group
        fields = ['id', 'name', 'permissions', 'users']

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

    @transaction.atomic()
    def create(self, validated_data):
        validated_data = {**validated_data, 'is_staff': True}
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

        send_email(user=user, context=context,
                   subject=subject, template=template)

        if self.group_ids:
            groups = Group.objects.filter(id__in=self.group_ids)
            user.groups.add(*groups)

        return user


class InviteStaffSerializer(BaseUserCreateSerializer):
    class Meta(BaseUserCreateSerializer.Meta):
        fields = ['email', 'groups', 'name']

    def validate(self, attrs):
        temporary_password = generate_random_password()
        attrs['password'] = temporary_password
        self.password = temporary_password
        self.groups = attrs.pop('groups', [])
        return super().validate(attrs)

    @transaction.atomic()
    def create(self, validated_data):
        temporary_password = self.password

        validated_data = {**validated_data, 'is_staff': True}
        user = super().create(validated_data)
        subject = "Invitation to Join the Walls Printing Team"
        context = {
            "user": user,
            "temporary_password": temporary_password,
            "invitation_link": os.getenv("STAFF_LOGIN_URL")
        }
        template = 'email/invitation_email.html'

        if self.groups:
            user.groups.add(*self.groups)

        send_email(user=user, context=context,
                   subject=subject, template=template)

        return user

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
        fields = ['name', 'username']

    def update(self, instance, validated_data):
        validated_data['is_staff'] = True
        user = super().update(instance, validated_data)

        return user


class CreateGroupSerializer(ModelSerializer):
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Group
        fields = ['id', 'name', 'permissions', 'user_ids']

    def create(self, validated_data):
        # Extract the user IDs from the validated data
        user_ids = validated_data.pop('user_ids', [])

        # Create the group
        group = super().create(validated_data)

        # Retrieve and add users to the group
        if user_ids:
            users = User.objects.filter(id__in=user_ids)
            group.user_set.add(*users)

        return group


class UpdateGroupSerializer(ModelSerializer):
    class Meta:
        model = Group
        fields = ['name', 'permissions']


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
