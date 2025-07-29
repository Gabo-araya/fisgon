# crawler/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import CrawlSession

class CrawlerConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add(
            "crawler_updates",
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            "crawler_updates",
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        # Procesar mensajes del cliente si es necesario
        pass

    async def crawler_update(self, event):
        # Enviar actualizaciones al cliente
        await self.send(text_data=json.dumps({
            'type': 'update',
            'message': event['message']
        }))