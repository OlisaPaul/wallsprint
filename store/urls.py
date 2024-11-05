from django.urls import include, path
from rest_framework_nested import routers
from . import views


router = routers.DefaultRouter()
router.register('quote-requests', views.QuoteRequestViewSet,
                basename='quote-requests'),
router.register('file-transfers', views.FileTransferViewSet,
                basename='file-transfers'),
router.register('images', views.ImageViewSet, basename='images'),
router.register('customers', views.CustomerViewSet, basename='customers'),
router.register('customer-groups', views.CustomerGroupViewSet,
                basename='customer-groups'),
router.register('requests', views.RequestViewSet, basename='requests'),
router.register('contact-us', views.ContactInquiryViewSet,
                basename='contact-us'),


# URLConf
urlpatterns = router.urls
