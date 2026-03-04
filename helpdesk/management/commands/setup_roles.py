from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from helpdesk.models import Incidencia, Equipo

class Command(BaseCommand):
    help = 'Crea los grupos de usuarios y configura permisos básicos.'

    def handle(self, *args, **kwargs):
        # Grupos requeridos
        grupos = ['ADMIN', 'SUPERVISOR', 'TECNICO']
        
        for g_name in grupos:
            group, created = Group.objects.get_or_create(name=g_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Grupo "{g_name}" creado con éxito.'))
            else:
                self.stdout.write(self.style.WARNING(f'Grupo "{g_name}" ya existía.'))
                
        # Esto de momento sirve como esqueleto. Los permisos detallados se manejan
        # mayormente a nivel de vistas usando decoradores/mixins que comprueban
        # el nombre del grupo. Podríamos asignar permisos de Django explícitamente:
        
        try:
            admin_group = Group.objects.get(name='ADMIN')
            # Asignar a ADMIN todo (o se hace is_superuser generalmente)
            
            sup_group = Group.objects.get(name='SUPERVISOR')
            # Permisos lectura
            
            tec_group = Group.objects.get(name='TECNICO')
            
        except Exception as e:
            pass

        self.stdout.write(self.style.SUCCESS('Configuración de roles completada.'))
