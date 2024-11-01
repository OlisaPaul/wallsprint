from django.contrib.auth.models import Group, Permission
from djoser.serializers import UserSerializer as BaseUserSerializer, UserCreateSerializer as BaseUserCreateSerializer
from djoser.conf import settings
from djoser.serializers import TokenCreateSerializer
from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from .models import User



class UserCreateSerializer(BaseUserCreateSerializer):
    class Meta(BaseUserCreateSerializer.Meta):
        fields = ['id', 'email', 'password', 'username', "name"]


class UserSerializer(BaseUserSerializer):
    class Meta(BaseUserSerializer.Meta):
        fields = ['id', 'email', 'name', 'username']
        read_only_fields = (settings.LOGIN_FIELD, 'email')


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
