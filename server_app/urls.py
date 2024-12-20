from django.urls import path
from .views import server_view

urlpatterns = [
    path('', server_view, name='server'),
]
