from django.urls import include, path
from rest_framework_nested import routers
from . import views


router = routers.DefaultRouter()
router.register('quote-request',
                views.QuoteRequestViewSet, basename='quote-request'),
router.register('images',
                views.ImageViewSet, basename='images'),
router.register('contact-us', views.ContactInquiryViewSet,
                basename='contact-us'),


# URLConf
urlpatterns = router.urls
