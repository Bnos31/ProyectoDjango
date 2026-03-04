from django.contrib import admin
from .models import Equipo, Incidencia, ComentarioIncidencia, AdjuntoIncidencia, AuditoriaAccion

admin.site.register(Equipo)
admin.site.register(Incidencia)
admin.site.register(ComentarioIncidencia)
admin.site.register(AdjuntoIncidencia)
admin.site.register(AuditoriaAccion)
