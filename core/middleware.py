from django.http import JsonResponse
from django.urls import resolve
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model

User = get_user_model()

class RoleBasedAccessMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        if not request.user.is_authenticated:
            return None  # Let unauthenticated requests (e.g., login) pass through

        # Get the current path and the resolved view name
        path = request.path
        view_name = resolve(path).view_name

        # Check if the path belongs to "customer" or "staff" endpoints
        if 'customers' in path and request.user.is_staff:
            return JsonResponse(
                {"detail": "Only customers are allowed to access this endpoint."},
                status=403
            )
        if 'staff' in path and not request.user.is_staff:
            return JsonResponse(
                {"detail": "Only staff are allowed to access this endpoint."},
                status=403
            )

        return None  # Allow the request to proceed
