from django.urls import path
from . import views

urlpatterns = [
    path('', views.root_view),  # Root endpoint
    path('chat/', views.chat_view),
    path('test/', views.test_view),
]