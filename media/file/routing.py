from django.urls import path
from . import cunsomer

ASGI_urlpatterns = [
    path('websocket/<str:full_name>',cunsomer.RealTime.as_asgi())
]