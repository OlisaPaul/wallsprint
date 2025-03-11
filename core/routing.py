from django.urls import re_path
from . import consumers
from store.consumers import  CustomerPermissionConsumer

websocket_urlpatterns = [
    re_path(r'ws/staff/permissions/',
            consumers.StaffPermissionConsumer.as_asgi()),
    re_path(r'ws/customer/permissions/$', CustomerPermissionConsumer.as_asgi()),
]
