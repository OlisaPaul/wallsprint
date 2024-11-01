from rest_framework import permissions


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
