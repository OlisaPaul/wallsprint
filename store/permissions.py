from rest_framework import permissions
from rest_framework.permissions import BasePermission
from ipware import get_client_ip
import requests

ALLOWED_TIMEZONES = {"Africa/Lagos", "America/New_York"}  # Example: Allow only certain time zones

class RestrictByTimezone(BasePermission):
    def has_permission(self, request, view):
        ip, _ = get_client_ip(request)
        print(ip)
        if not ip:
            return False  # No IP found, deny access

        # Get time zone using an external API
        try:
            response = requests.get(f"http://ip-api.com/json/{'105.115.2.134'}").json()
            timezone = response.get("timezone")
            print(timezone)
            if timezone in ALLOWED_TIMEZONES:
                return True
        except Exception as e:
            print(f"Timezone check failed: {e}")
            return False  # Fail-safe: Deny access if lookup fails

        return False

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)


class FullDjangoModelPermissions(permissions.DjangoModelPermissions):
    def __init__(self):
        self.perms_map['GET'] = ['%(app_label)s.view_%(model_name)s']


class ViewCustomerHistoryPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.has_perm('store.view_history')
    
def create_permission_class(perm_string):
    """
    Function to create a custom permission class based on the permission string.
    """
    class DynamicPermission(permissions.BasePermission):
        """
        Custom permission to check if the user has the specified permission.
        """
        def has_permission(self, request, view):
            return request.user.has_perm(perm_string)

    return DynamicPermission
