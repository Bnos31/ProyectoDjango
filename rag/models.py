import json
from django.db import models
from django.contrib.auth.models import User


class DocumentoRAG(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('indexando', 'Indexando'),
        ('indexado', 'Indexado'),
        ('error', 'Error'),
    ]

    nombre = models.CharField(max_length=255, verbose_name='Nombre')
    archivo = models.FileField(upload_to='documentos_rag/', verbose_name='Archivo PDF')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    num_chunks = models.IntegerField(default=0, verbose_name='Fragmentos indexados')
    error_mensaje = models.TextField(blank=True, null=True)
    subido_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='documentos_rag'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Documento RAG'
        verbose_name_plural = 'Documentos RAG'

    def __str__(self):
        return self.nombre


class ConsultaRAG(models.Model):
    pregunta = models.TextField(verbose_name='Pregunta')
    respuesta = models.TextField(verbose_name='Respuesta')
    fuentes = models.TextField(blank=True, default='[]')  # JSON serializado
    usuario = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='consultas_rag'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Consulta RAG'
        verbose_name_plural = 'Consultas RAG'

    def get_fuentes(self):
        try:
            return json.loads(self.fuentes)
        except Exception:
            return []

    def __str__(self):
        usuario = self.usuario.username if self.usuario else 'Anónimo'
        return f"{usuario} — {self.pregunta[:60]}"
