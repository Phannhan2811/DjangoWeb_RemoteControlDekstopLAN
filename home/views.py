from django.shortcuts import render

def home_view(request):
    return render(request, 'home/home.html')

# Tạo URL trong home/urls.py
from django.urls import path
from .views import home_view

urlpatterns = [
    path('', home_view, name='home'),
]



