import json
from django.http import JsonResponse
from django.urls import resolve
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response


User = get_user_model()


class RoleBasedAccessMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        path = request.path
        view_name = resolve(path).view_name

        # Attempt token validation explicitly
        jwt_auth = JWTAuthentication()
        if request.headers.get('Authorization'):
            try:
                user, token = jwt_auth.authenticate(request)
                print(f"Authenticated user: {user}")
                request.user = user  # Forcefully set user for the request
            except AuthenticationFailed as e:
                print(f"Authentication failed: {e}")

        if 'auth' in path and not 'confirm' in path:
            user = request.user
            
            if not request.user.is_authenticated:
                if not any(substring in path for substring in ['create', 'reset_password']):
                    return JsonResponse({"detail": "Authentication credentials were not provided."}, status=401)
                elif request.method == 'POST':
                    data = {}
                    if request.content_type.startswith("multipart/form-data"):
                        data = request.POST
                    else:
                        decoded_body = request.body.decode('utf-8').replace('\r\n', '')
                        print(f"Decoded Body: {decoded_body}") 

                        data = json.loads(decoded_body)
                    email = data.get('email')

                    if not email:
                        return JsonResponse({"detail": "email is required"}, status=400)
                    
                    user = User.objects.get(email=email)
                else:
                    return None
                   
            # Check if the path belongs to "customer" or "staff" endpoints
            if 'customer' in path and user.is_staff:
                return JsonResponse(
                    {"detail": "Only customers are allowed to access this endpoint."},
                    status=403
                )
            elif not 'customer' in path and not user.is_staff:
                return JsonResponse(
                    {"detail": "Only staff are allowed to access this endpoint."},
                    status=403
                )

            return None

        return None  # Allow the request to proceed
