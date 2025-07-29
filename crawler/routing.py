# crawler/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/crawler/$', consumers.CrawlerConsumer.as_asgi()),
]