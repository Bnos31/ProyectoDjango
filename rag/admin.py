from django.contrib import admin
from .models import DocumentoRAG, ConsultaRAG


@admin.register(DocumentoRAG)
class DocumentoRAGAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'estado', 'num_chunks', 'subido_por', 'created_at']
    list_filter = ['estado']
    readonly_fields = ['created_at', 'updated_at', 'num_chunks', 'estado', 'error_mensaje']


@admin.register(ConsultaRAG)
class ConsultaRAGAdmin(admin.ModelAdmin):
    list_display = ['pregunta', 'usuario', 'created_at']
    readonly_fields = ['created_at', 'fuentes']
