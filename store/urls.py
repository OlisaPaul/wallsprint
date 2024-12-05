from django.urls import include, path
from rest_framework_nested import routers
from . import views


router = routers.DefaultRouter()
router.register("carts", views.CartViewSet, basename="carts")
router.register('quote-requests', views.QuoteRequestViewSet,
                basename='quote-requests'),
router.register('file-transfers', views.FileTransferViewSet,
                basename='file-transfers'),
router.register('images', views.ImageViewSet, basename='images'),
router.register('catalogs', views.CatalogViewSet, basename='catalogs'),
router.register("orders", views.OrderViewSet, basename='orders')
# router.register(r'catalog-items', views.CatalogItemViewSet, basename='catalog-item')
router.register('portals', views.PortalViewSet, basename='portals'),
router.register('html-files', views.HTMLFileViewSet, basename='html-files'),
router.register('customers', views.CustomerViewSet, basename='customers'),
router.register('customer-groups', views.CustomerGroupViewSet,
                basename='customer-groups'),
router.register('requests', views.RequestViewSet, basename='requests'),
# router.register('message-center', views.MessageCenterViewSet, basename='message-center'),
router.register('contact-us', views.ContactInquiryViewSet,
                basename='contact-us'),
portals_router = routers.NestedDefaultRouter(
    router, 'portals', lookup='portal')
portals_router.register(
    'contents', views.PortalContentViewSet, basename='portal-contents')
catalogs_router = routers.NestedDefaultRouter(
    router, 'catalogs', lookup='catalog')
catalogs_router.register(
    'items', views.CatalogItemViewSet, basename='catalog-items')
carts_router = routers.NestedDefaultRouter(router, "carts", lookup='cart')
carts_router.register("items", views.CartItemViewSet, basename="cart-items")


message_centre_url = [
    path('message-center/', views.MessageCenterView.as_view(), name='message-center'),
]


# URLConf
urlpatterns = router.urls + portals_router.urls + \
    catalogs_router.urls + message_centre_url + carts_router.urls
