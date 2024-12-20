from django.urls import path
from .views import client_view

urlpatterns = [
    path('', client_view, name='client'),
]
