"""
URL configuration for wallsprint project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include, re_path
from django.contrib.auth.views import LoginView
from rest_framework.routers import DefaultRouter
import debug_toolbar
from core.forms import AuthenticationForm
from core.views import GroupViewSet, PermissionViewSet, StaffViewSet


router = DefaultRouter()
router.register(r'api/v1/auth/groups', GroupViewSet, basename='group')
router.register(r'api/v1/auth/permissions',
                PermissionViewSet, basename='permission')
router.register(r'api/v1/auth/staffs',
                StaffViewSet, basename='staffs')

urlpatterns = [
    re_path(r'^accounts/login/$',
            LoginView.as_view(authentication_form=AuthenticationForm), name='login'),
    re_path(r'^accounts/', include('django.contrib.auth.urls')),
    path('', include(router.urls)),
    path('api/v1/admin/', admin.site.urls),
    path('api/v1/core/', include('core.urls')),
    path('api/v1/store/', include('store.urls')),
    path('api/v1/auth/', include('djoser.urls')),
    path('api/v1/auth/', include('djoser.urls.jwt')),
    path('api/v1/auth/customer/', include('djoser.urls')),
    path('api/v1/auth/customer/', include('djoser.urls.jwt')),
    path('__debug__/', include(debug_toolbar.urls)),
] 

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
