import pandas as pd
from helpdesk.models import Incidencia

def load_dataset():
    """
    Lee los datos históricos de Incidencia desde Django ORM y los convierte en un DataFrame.
    Prepara la variable objetivo 'falla_critica'.
    """
    # Usar select_related para optimizar la consulta del equipo
    incidencias = Incidencia.objects.select_related('equipo').all()
    
    data = []
    for inc in incidencias:
        data.append({
            'equipo_nombre': inc.equipo.nombre,
            'estado': inc.estado,
            'tiene_tecnico': 1 if inc.tecnico_asignado else 0,
            # Regla simple: 1 si la prioridad es alta o crítica, 0 de lo contrario
            'falla_critica': 1 if inc.prioridad in ['ALTA', 'CRITICA'] else 0
        })
        
    df = pd.DataFrame(data)
    return df
