import json
from django.http import JsonResponse
from django.urls import resolve
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from .models import BlacklistedToken
import hashlib


User = get_user_model()


class RoleBasedAccessMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        path = request.path
        view_name = resolve(path).view_name
        if not 'auth' in request.path or 'logout' in request.path:
            return None

        # Attempt token validation explicitly

        if 'auth' in path and not 'confirm' in path:
            jwt_auth = JWTAuthentication()
            if request.headers.get('Authorization'):
                try:
                    if jwt_auth.authenticate(request):
                        user, token = jwt_auth.authenticate(request)
                        request.user = user
                    else:
                        return JsonResponse({
                            "detail": "Given token not valid for any token type",
                            "code": "token_not_valid",
                            "messages": [
                                {
                                    "token_class": "AccessToken",
                                    "token_type": "access",
                                    "message": "Token is invalid or expired"
                                }
                            ]
                        }, status=401)
                except AuthenticationFailed as e:
                    print(f"Authentication failed: {e}")

            user = request.user

            if not request.user.is_authenticated:
                if request.user.is_active != False:
                    return JsonResponse({"detail": "User is inactive."}, status=403)
                if not any(substring in path for substring in ['create', 'reset_password', 'logout']):
                    return JsonResponse({"detail": "Authentication credentials were not provided."}, status=401)
                elif request.method == 'POST':
                    data = {}
                    if request.content_type.startswith("multipart/form-data"):
                        data = request.POST
                    else:
                        decoded_body = request.body.decode(
                            'utf-8').replace('\r\n', '')
                        print(f"Decoded Body: {decoded_body}")

                        data = json.loads(decoded_body)
                    email = data.get('email')

                    if not email:
                        return JsonResponse({"detail": "email is required"}, status=400)

                    try:
                        user = User.objects.get(email=email)
                    except User.DoesNotExist:
                        return JsonResponse({"detail": "User not found"}, status=404)
                else:
                    return None

            # Check if the path belongs to "customer" or "staff" endpoints
            if 'customer' in path and user.is_staff:
                return JsonResponse(
                    {"detail": "Only customers are allowed to access this page."},
                    status=403
                )
            elif not 'customer' in path and not user.is_staff:
                return JsonResponse(
                    {"detail": "Only staff are allowed to access this page."},
                    status=403
                )

            return None

        return None  # Allow the request to proceed

def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


class TokenBlacklistMiddleware(MiddlewareMixin):
    def process_request(self, request):
        auth_header = request.headers.get('Authorization')
        if auth_header:
            token = auth_header.split(' ')[1]  # Assuming 'Bearer <token>'
            hashed_token = hash_token(token)
            if BlacklistedToken.objects.filter(token_hash=hashed_token).exists():
                return JsonResponse({'detail': 'Token is blacklisted'}, status=401)
