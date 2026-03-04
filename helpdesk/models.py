from django.db import models
from django.contrib.auth.models import User

class Equipo(models.Model):
    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    ubicacion = models.CharField(max_length=100, null=True, blank=True, verbose_name="Ubicación")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

class Incidencia(models.Model):
    PRIORIDAD_CHOICES = [
        ('BAJA', 'Baja'),
        ('MEDIA', 'Media'),
        ('ALTA', 'Alta'),
        ('CRITICA', 'Crítica'),
    ]

    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('EN_PROCESO', 'En Proceso'),
        ('RESUELTO', 'Resuelto'),
        ('CERRADO', 'Cerrado'),
    ]

    codigo = models.CharField(max_length=20, unique=True, editable=False)
    titulo = models.CharField(max_length=200, verbose_name="Título")
    descripcion = models.TextField(verbose_name="Descripción")
    prioridad = models.CharField(max_length=15, choices=PRIORIDAD_CHOICES, default='BAJA')
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='PENDIENTE')
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name='incidencias')
    creado_por = models.ForeignKey(User, on_delete=models.CASCADE, related_name='incidencias_creadas')
    tecnico_asignado = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='incidencias_asignadas', limit_choices_to={'groups__name': 'TECNICO'})
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.codigo:
            # Obtener el último ID o contar elementos para generar INC-00000X
            last_incidencia = Incidencia.objects.order_by('id').last()
            if not last_incidencia:
                new_id = 1
            else:
                new_id = last_incidencia.id + 1
            self.codigo = f"INC-{new_id:06d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} - {self.titulo}"

class ComentarioIncidencia(models.Model):
    incidencia = models.ForeignKey(Incidencia, on_delete=models.CASCADE, related_name='comentarios')
    autor = models.ForeignKey(User, on_delete=models.CASCADE)
    comentario = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comentario de {self.autor.username} en {self.incidencia.codigo}"

class AdjuntoIncidencia(models.Model):
    incidencia = models.ForeignKey(Incidencia, on_delete=models.CASCADE, related_name='adjuntos')
    subido_por = models.ForeignKey(User, on_delete=models.CASCADE)
    archivo = models.FileField(upload_to='adjuntos/%Y/%m/%d/')
    created_at = models.DateTimeField(auto_now_add=True)

class AuditoriaAccion(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    accion = models.CharField(max_length=100) # ej: CAMBIO_ESTADO, ASIGNACION_TECNICO
    detalle = models.TextField()
    incidencia = models.ForeignKey(Incidencia, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.usuario.username} - {self.accion} - {self.created_at}"
