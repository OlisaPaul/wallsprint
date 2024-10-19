from django.urls import include, path
from rest_framework_nested import routers
from . import views


router = routers.DefaultRouter()
router.register("groups", views.GroupViewSet, basename="groups")
router.register("permissions", views.PermissionViewSet, basename="permissions")

urlpatterns = router.urls