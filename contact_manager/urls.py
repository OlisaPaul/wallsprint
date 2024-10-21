from django.urls import include, path
from rest_framework_nested import routers
from . import views


router = routers.DefaultRouter()
# router.register('project-quote-request',
#                 views.ProjectQuoteRequest, basename='project-quote-request'),
router.register('contact-us', views.ContactInquiryViewSet, basename='contact-us'),


# URLConf
urlpatterns = router.urls
