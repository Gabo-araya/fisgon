from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/crawler/', consumers.CrawlerConsumer.as_asgi()),
    path('ws/crawler/session/<int:session_id>/', consumers.SessionConsumer.as_asgi()),
]
