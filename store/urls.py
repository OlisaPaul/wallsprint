from django.urls import include, path
from rest_framework_nested import routers
from . import views


router = routers.DefaultRouter()
router.register("carts", views.CartViewSet, basename="carts")
router.register('quote-requests', views.QuoteRequestViewSet,
                basename='quote-requests'),
router.register('file-transfers', views.FileTransferViewSet,
                basename='file-transfers'),
router.register('transfer-files', views.FileExchangeViewSet,
                basename='transfer-files'),
router.register('online-proofs', views.OnlineProofViewSet,
                basename='online-proofs'),
router.register('images', views.ImageViewSet, basename='images'),
router.register('catalogs', views.CatalogViewSet, basename='catalogs'),
router.register('catalog-items', views.CatalogItemViewSet, basename='catalog-items'),
router.register("orders", views.OrderViewSet, basename='orders')
# router.register(r'catalog-items', views.CatalogItemViewSet, basename='catalog-item')
router.register('portals', views.PortalViewSet, basename='portals'),
router.register('pages', views.HTMLFileViewSet, basename='pages'),
router.register('customers', views.CustomerViewSet, basename='customers'),
router.register('customer-groups', views.CustomerGroupViewSet,
                basename='customer-groups'),
router.register('requests', views.RequestViewSet, basename='requests'),
router.register('portal-content-catalogs',
                views.PortalContentCatalogViewSet, basename='portal-content-catalogs'),
router.register('online-payments', views.OnlinePaymentViewSet,
                basename='online-payments'),
router.register('contact-us', views.ContactInquiryViewSet,
                basename='contact-us'),
portals_router = routers.NestedDefaultRouter(
    router, 'portals', lookup='portal',)
portals_router.register(
    'contents', views.PortalContentViewSet, basename='portal-contents')
contents_router = routers.NestedDefaultRouter(
    portals_router, r'contents', lookup='content')
contents_router.register(
    r'catalogs', views.PortalContentCatalogViewSet, basename='content-catalogs')
catalogs_router = routers.NestedDefaultRouter(
    router, 'catalogs', lookup='catalog')
catalogs_router.register(
    'items', views.CatalogItemViewSet, basename='catalog-items')
carts_router = routers.NestedDefaultRouter(router, "carts", lookup='cart')
carts_router.register("items", views.CartItemViewSet, basename="cart-items")
requests_router = routers.NestedDefaultRouter(
    router, 'requests', lookup='request')
requests_router.register(
    'notes', views.NoteViewSet, basename='request-notes')
file_transfers_router = routers.NestedDefaultRouter(
    router, 'file-transfers', lookup='file_transfer')
file_transfers_router.register(
    'notes', views.NoteViewSet, basename='file-transfer-notes')
requests_router.register(
    'billing-info', views.BillingInfoViewSet, basename='request-billing-info'
)
file_transfers_router.register(
    'billing-info', views.BillingInfoViewSet, basename='file-transfer-billing-info'
)
orders_router = routers.NestedDefaultRouter(router, 'orders', lookup='order')
orders_router.register('notes', views.NoteViewSet, basename='order-notes')
orders_router.register('shipments', views.ShipmentViewSet, basename='order-shipments')
orders_router.register('transactions', views.TransactionViewSet, basename='order-transactions')
orders_router.register('items', views.OrderItemViewSet, basename='order-items')
requests_router.register(
    'shipments', views.ShipmentViewSet, basename='request-shipments'
)
file_transfers_router.register(
    'shipments', views.ShipmentViewSet, basename='file-transfer-shipments'
)
requests_router.register(
    'transactions', views.TransactionViewSet, basename='request-transactions'
)
file_transfers_router.register(
    'transactions', views.TransactionViewSet, basename='file-transfer-transactions'
)

message_centre_url = [
    path('message-center/', views.MessageCenterView.as_view(), name='message-center'),
]

recent_order_url = [
    path('recent-orders/', views.OrderView.as_view(), name='recent-orders'),
]

# Create a nested router for CartDetails under CartItems
cart_items_router = routers.NestedDefaultRouter(
    carts_router, 'items', lookup='item')
cart_items_router.register(
    'details', views.ItemDetailsViewSet, basename='cart-details')
catalog_items_router = routers.NestedDefaultRouter(
    catalogs_router, 'items', lookup='catalog_item')
catalog_items_router.register(
    'attributes', views.AttributeViewSet, basename='attributes'
)
attributes_router = routers.NestedDefaultRouter(
    catalog_items_router, 'attributes', lookup='attribute')
attributes_router.register(
    'options', views.AttributeOptionViewSet, basename='attribute-options'
)    
# URLConf
urlpatterns = router.urls + portals_router.urls + \
    catalogs_router.urls + message_centre_url + carts_router.urls +\
    contents_router.urls + recent_order_url + \
    requests_router.urls + file_transfers_router.urls + \
    cart_items_router.urls + orders_router.urls +\
    catalog_items_router.urls + attributes_router.urls
