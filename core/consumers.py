from channels.generic.websocket import AsyncWebsocketConsumer
import json
import logging

logger = logging.getLogger(__name__)


class StaffPermissionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Join staff_permissions group
        await self.channel_layer.group_add("staff_permissions", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Leave staff_permissions group
        await self.channel_layer.group_discard("staff_permissions", self.channel_name)

    # async def permissions_update(self, event):
    #     # Send message to WebSocket
    #     await self.send(text_data=json.dumps({
    #         "type": "permissions_update",
    #         "user_id": event["user_id"],
    #         "permissions": event["permissions"]
    #     }))

    async def bulk_permissions_update(self, event):
        # Send bulk update message to WebSocket
        await self.send(text_data=json.dumps({
            "type": "bulk_permissions_update",
            "updates": event["updates"]
        }))
