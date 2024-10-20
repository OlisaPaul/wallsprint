from django.contrib.auth.models import Group, Permission
from djoser.serializers import UserSerializer as BaseUserSerializer, UserCreateSerializer as BaseUserCreateSerializer
from djoser.conf import settings
from djoser.serializers import TokenCreateSerializer
from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer


class UserCreateSerializer(BaseUserCreateSerializer):
    class Meta(BaseUserCreateSerializer.Meta):
        fields = ['id', 'email', 'password', 'first_name', 'last_name']


class UserSerializer(BaseUserSerializer):
    class Meta(BaseUserSerializer.Meta):
        fields = ['id', 'email', 'first_name', 'last_name']
        read_only_fields = (settings.LOGIN_FIELD, 'email')


class PermissionSerializer(ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename', 'content_type']


class GroupSerializer(ModelSerializer):
    permissions = PermissionSerializer(many=True)

    class Meta:
        model = Group
        fields = ['id', 'name', 'permissions']

class CreateGroupSerializer(ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name', 'permissions']


class AddUserToGroupSerializer(ModelSerializer):
    user_id = serializers.IntegerField()

    class Meta:
        model = Group
        fields = ['user_id']


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
