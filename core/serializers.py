import os
from django.db import transaction
from django.contrib.auth.models import Group, Permission
from djoser.serializers import UserSerializer as BaseUserSerializer, UserCreateSerializer as BaseUserCreateSerializer, UserDeleteSerializer
from djoser.conf import settings
from djoser.serializers import TokenCreateSerializer
from django.contrib.auth import authenticate
from dotenv import load_dotenv
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string

load_dotenv()

class CustomUserDeleteSerializer(UserDeleteSerializer):
    current_password = serializers.CharField(style={"input_type": "password"}, required=False)

class UserSerializer(BaseUserSerializer):
    groups = serializers.SerializerMethodField()

    class Meta(BaseUserSerializer.Meta):
        fields = ['id', 'email', 'name', 'username',
                  'is_staff', 'is_superuser', 'groups']
        read_only_fields = (settings.LOGIN_FIELD, 'email',
                            'is_staff', 'is_superuser', 'groups', 'username')

    def get_groups(self, obj):
        # Return the count of groups the user is in
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
        # Get all users in the group and serialize them
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
        temporary_password = validated_data.get("password")  # or another method if needed
        self.send_welcome_email(user, temporary_password)

        if self.group_ids:
            groups = Group.objects.filter(id__in=self.group_ids)
            user.groups.add(*groups)

        return user
    
    def send_welcome_email(self, user: User, temporary_password):
        subject = "Welcome to Walls Printing!"
        message = render_to_string("email/welcome_email.html", {
            "user": user,
            "temporary_password": temporary_password,
            "login_url": "https://example.com/login"  
        })
        send_mail(
            subject,
            message,
            os.getenv('EMAIL_HOST_USER'),
            [user.email],
            fail_silently=False,
            html_message=message
        )



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
