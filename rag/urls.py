from django.urls import path
from . import views

app_name = 'rag'

urlpatterns = [
    path('upload/', views.upload_documento, name='upload'),
    path('documentos/', views.lista_documentos, name='documentos'),
    path('documentos/<int:pk>/eliminar/', views.eliminar_documento, name='eliminar'),
    path('chat/', views.chat_rag, name='chat'),
    path('api/consultar/', views.consultar_ajax, name='consultar_ajax'),
]
