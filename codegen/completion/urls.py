from django.urls import path
from . import views

urlpatterns = [
    path("health", views.health, name="health"),
    path("completion", views.completion, name="completion"),
    path("chat", views.chat, name="chat"),
    path("models", views.models, name="models"),
    path("rag/index", views.rag_index, name="rag_index"),
]
