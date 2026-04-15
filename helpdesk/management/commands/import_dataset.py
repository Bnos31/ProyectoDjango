"""
Comando de gestión para importar el dataset Excel de Grinding al modelo Django.

Uso:
    python manage.py import_dataset <ruta_al_excel>

Ejemplo:
    python manage.py import_dataset "C:/Users/limps/Downloads/Dataset_Grinding.xlsx"
"""

import pandas as pd
from datetime import timedelta
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.utils import timezone

from helpdesk.models import Equipo, Incidencia


# Mapeo de criticidad del Excel al campo prioridad del modelo Django
CRITICIDAD_MAP = {
    'Alta': 'ALTA',
    'Media': 'MEDIA',
    'Baja': 'BAJA',
    'Crítica': 'CRITICA',
    'Critica': 'CRITICA',
}

# Mapeo de estado del Excel al campo estado del modelo Django
ESTADO_MAP = {
    'Cerrado': 'CERRADO',
    'Pendiente': 'PENDIENTE',
    'En Proceso': 'EN_PROCESO',
    'Resuelto': 'RESUELTO',
}


class Command(BaseCommand):
    help = 'Importa el dataset Excel de incidencias de equipos de grinding al sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            'excel_path',
            type=str,
            help='Ruta absoluta al archivo Excel del dataset',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Eliminar todos los equipos e incidencias existentes antes de importar',
        )

    def handle(self, *args, **options):
        excel_path = options['excel_path']

        # Obtener usuario del sistema para asignar como creador
        try:
            system_user = User.objects.filter(is_superuser=True).first()
            if not system_user:
                system_user = User.objects.first()
            if not system_user:
                raise CommandError(
                    "No existe ningún usuario en el sistema. "
                    "Crea un superusuario primero con: python manage.py createsuperuser"
                )
        except Exception as e:
            raise CommandError(f"Error al obtener usuario del sistema: {e}")

        # Limpiar datos existentes si se indica
        if options['clear']:
            self.stdout.write(self.style.WARNING('Eliminando datos existentes...'))
            Incidencia.objects.all().delete()
            Equipo.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Datos eliminados.'))

        # Cargar el Excel
        self.stdout.write(f'Cargando archivo: {excel_path}')
        try:
            df = pd.read_excel(excel_path)
        except FileNotFoundError:
            raise CommandError(f"Archivo no encontrado: {excel_path}")
        except Exception as e:
            raise CommandError(f"Error al leer el Excel: {e}")

        self.stdout.write(f'Dataset cargado: {len(df)} filas, columnas: {list(df.columns)}')

        # Renombrar columnas para evitar problemas de encoding
        df.columns = [
            'id_activo', 'nombre_equipo', 'marca_modelo', 'ubicacion',
            'fecha_incidencia', 'tipo_mant', 'falla_detectada',
            'causa_raiz', 'accion_correctiva', 'repuestos',
            'criticidad', 'estado',
        ]

        equipos_creados = 0
        equipos_existentes = 0
        incidencias_creadas = 0
        incidencias_error = 0

        # Procesar cada fila
        for idx, row in df.iterrows():
            try:
                # --- Crear o recuperar Equipo ---
                codigo = str(row['id_activo']).strip()
                nombre = str(row['nombre_equipo']).strip()
                ubicacion = str(row['ubicacion']).strip() if pd.notna(row['ubicacion']) else ''

                equipo, created = Equipo.objects.get_or_create(
                    codigo=codigo,
                    defaults={
                        'nombre': nombre,
                        'ubicacion': ubicacion,
                        'activo': True,
                    }
                )
                if created:
                    equipos_creados += 1
                else:
                    equipos_existentes += 1

                # --- Mapear campos ---
                criticidad_raw = str(row['criticidad']).strip()
                prioridad = CRITICIDAD_MAP.get(criticidad_raw, 'MEDIA')

                estado_raw = str(row['estado']).strip()
                estado = ESTADO_MAP.get(estado_raw, 'CERRADO')

                tipo_mant = str(row['tipo_mant']).strip() if pd.notna(row['tipo_mant']) else ''
                falla = str(row['falla_detectada']).strip() if pd.notna(row['falla_detectada']) else ''
                causa = str(row['causa_raiz']).strip() if pd.notna(row['causa_raiz']) else ''
                accion = str(row['accion_correctiva']).strip() if pd.notna(row['accion_correctiva']) else ''
                repuestos = str(row['repuestos']).strip() if pd.notna(row['repuestos']) else ''
                marca = str(row['marca_modelo']).strip() if pd.notna(row['marca_modelo']) else ''

                # Título de la incidencia
                titulo = f"[{tipo_mant}] {falla}" if falla else f"[{tipo_mant}] Incidencia"
                titulo = titulo[:200]  # Limitar al max_length del campo

                # Descripción detallada
                descripcion = (
                    f"Causa raíz: {causa}\n"
                    f"Acción correctiva: {accion}\n"
                    f"Repuestos utilizados: {repuestos}\n"
                    f"Marca/Modelo: {marca}"
                )

                # Fecha de incidencia
                fecha_incidencia = row['fecha_incidencia']
                if pd.isna(fecha_incidencia):
                    fecha_incidencia = timezone.now()
                else:
                    # Convertir a datetime con timezone
                    fecha_incidencia = pd.Timestamp(fecha_incidencia).to_pydatetime()
                    if timezone.is_naive(fecha_incidencia):
                        fecha_incidencia = timezone.make_aware(fecha_incidencia)

                # Fecha cierre: si está cerrado, se cierra al día siguiente
                fecha_cierre = None
                if estado in ['CERRADO', 'RESUELTO']:
                    fecha_cierre = fecha_incidencia + timedelta(days=1)

                # --- Crear Incidencia ---
                incidencia = Incidencia(
                    titulo=titulo,
                    descripcion=descripcion,
                    prioridad=prioridad,
                    estado=estado,
                    equipo=equipo,
                    creado_por=system_user,
                    tecnico_asignado=None,
                    fecha_cierre=fecha_cierre,
                )
                incidencia.save()

                # Actualizar fecha_creacion usando queryset.update() para
                # saltarse el auto_now_add y registrar la fecha real del dataset
                Incidencia.objects.filter(pk=incidencia.pk).update(
                    fecha_creacion=fecha_incidencia,
                    created_at=fecha_incidencia,
                )

                incidencias_creadas += 1

            except Exception as e:
                incidencias_error += 1
                self.stdout.write(
                    self.style.ERROR(f'  Fila {idx + 2}: Error - {e}')
                )

        # Resumen final
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS('IMPORTACIÓN COMPLETADA'))
        self.stdout.write('=' * 50)
        self.stdout.write(f'  Equipos creados:     {equipos_creados}')
        self.stdout.write(f'  Equipos existentes:  {equipos_existentes}')
        self.stdout.write(f'  Incidencias creadas: {incidencias_creadas}')
        if incidencias_error:
            self.stdout.write(self.style.WARNING(f'  Errores:             {incidencias_error}'))
        self.stdout.write('=' * 50)
