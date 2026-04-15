"""
dataset.py — Carga y prepara el dataset desde Django ORM.

Extrae incidencias de la base de datos y genera un DataFrame con:
  - Features: equipo, estado, tecnico_asignado, mes_reporte, dias_resolucion
  - Target:   falla_critica (1 = prioridad ALTA o CRITICA, 0 = otro)
"""

import pandas as pd
import django


def load_dataset():
    """
    Carga las incidencias desde Django ORM y retorna un DataFrame de pandas.

    Returns:
        pd.DataFrame: DataFrame con features y variable objetivo 'falla_critica'.

    Raises:
        ValueError: Si no hay datos suficientes en la base de datos.
    """
    # Importar modelos aquí para evitar importación circular en contexto manage.py shell
    from helpdesk.models import Incidencia

    # Obtener todas las incidencias con sus relaciones
    queryset = Incidencia.objects.select_related('equipo', 'tecnico_asignado').all()

    if not queryset.exists():
        raise ValueError(
            "No hay incidencias en la base de datos. "
            "Ejecuta primero: python manage.py import_dataset <ruta_excel>"
        )

    registros = []
    for inc in queryset:
        # Calcular días de resolución (-1 si aún no está cerrada)
        if inc.fecha_cierre and inc.fecha_creacion:
            delta = inc.fecha_cierre - inc.fecha_creacion
            dias_resolucion = max(delta.days, 0)
        else:
            dias_resolucion = -1

        # Mes de reporte (1-12) y día de la semana (0=lunes, 6=domingo)
        mes_reporte = inc.fecha_creacion.month if inc.fecha_creacion else 1
        dia_semana = inc.fecha_creacion.weekday() if inc.fecha_creacion else 0

        # Técnico asignado (nombre o 'Sin asignar')
        tecnico = (
            inc.tecnico_asignado.username
            if inc.tecnico_asignado
            else 'Sin asignar'
        )

        # Variable objetivo: 1 si prioridad es ALTA o CRITICA
        falla_critica = 1 if inc.prioridad in ['ALTA', 'CRITICA'] else 0

        registros.append({
            'equipo': inc.equipo.nombre,
            'estado': inc.estado,
            'tecnico_asignado': tecnico,
            'mes_reporte': mes_reporte,
            'dia_semana': dia_semana,
            'dias_resolucion': dias_resolucion,
            'falla_critica': falla_critica,
        })

    df = pd.DataFrame(registros)
    print(f"[dataset] Dataset cargado: {len(df)} registros | "
          f"Críticos: {df['falla_critica'].sum()} ({df['falla_critica'].mean()*100:.1f}%)")

    return df
