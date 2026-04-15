"""
predict.py — Carga el modelo entrenado y predice probabilidad de falla crítica.

Uso:
    from helpdesk.ml.predict import predict_failure

    data = {
        'equipo': 'Motor Eléctrico',
        'estado': 'CERRADO',
        'tecnico_asignado': 'Sin asignar',
        'mes_reporte': 3,
        'dia_semana': 1,
        'dias_resolucion': 2,
    }
    resultado = predict_failure(data)
    print(resultado['probabilidad'])  # e.g. 0.72 → 72%
"""

import os
import joblib
import pandas as pd

# Rutas de los artefactos del modelo
ML_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(ML_DIR, 'model.pkl')
ENCODERS_PATH = os.path.join(ML_DIR, 'encoders.pkl')

# Columnas categóricas (deben coincidir con train_model.py)
CATEGORICAL_COLS = ['equipo', 'estado', 'tecnico_asignado']
FEATURE_COLS = ['equipo', 'estado', 'tecnico_asignado', 'mes_reporte', 'dia_semana', 'dias_resolucion']

# Caché del modelo cargado (evita recargar en cada petición)
_model_cache = None
_encoders_cache = None


def _load_artifacts():
    """Carga el modelo y los encoders desde disco (con caché en memoria)."""
    global _model_cache, _encoders_cache

    if _model_cache is None:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"Modelo no encontrado en {MODEL_PATH}. "
                "Ejecuta primero train_model() para entrenar el modelo."
            )
        _model_cache = joblib.load(MODEL_PATH)

    if _encoders_cache is None:
        if not os.path.exists(ENCODERS_PATH):
            raise FileNotFoundError(
                f"Encoders no encontrados en {ENCODERS_PATH}."
            )
        _encoders_cache = joblib.load(ENCODERS_PATH)

    return _model_cache, _encoders_cache


def predict_failure(data: dict) -> dict:
    """
    Predice la probabilidad de falla crítica de un equipo.

    Args:
        data (dict): Diccionario con las features del equipo:
            - equipo (str): Nombre del equipo
            - estado (str): Estado de la última incidencia
            - tecnico_asignado (str): Usuario del técnico o 'Sin asignar'
            - mes_reporte (int): Mes de la última incidencia (1-12)
            - dia_semana (int): Día de la semana (0=lunes, 6=domingo)
            - dias_resolucion (int): Días que tardó en resolverse (-1 si no aplica)

    Returns:
        dict: {
            'probabilidad': float (0.0 a 1.0),
            'porcentaje': float (0.0 a 100.0),
            'nivel_riesgo': str ('Bajo', 'Medio', 'Alto'),
            'clase': int (0 o 1),
        }

    Raises:
        FileNotFoundError: Si el modelo no ha sido entrenado.
    """
    model, encoders = _load_artifacts()

    # Crear DataFrame con una sola fila
    df = pd.DataFrame([data])

    # Codificar variables categóricas usando los encoders del entrenamiento
    for col in CATEGORICAL_COLS:
        le = encoders[col]
        valor = str(df[col].iloc[0])

        # Si el valor no fue visto durante el entrenamiento, usar el más frecuente
        if valor not in le.classes_:
            valor = le.classes_[0]

        df[col] = le.transform([valor])

    # Asegurar el orden correcto de columnas
    X = df[FEATURE_COLS]

    # Predecir probabilidades
    proba = model.predict_proba(X)[0]
    clase_idx = 1  # Índice de la clase "falla_critica=1"
    probabilidad = float(proba[clase_idx])
    porcentaje = probabilidad * 100

    # Determinar nivel de riesgo según los umbrales definidos
    if porcentaje < 30:
        nivel_riesgo = 'Bajo'
    elif porcentaje < 70:
        nivel_riesgo = 'Medio'
    else:
        nivel_riesgo = 'Alto'

    return {
        'probabilidad': probabilidad,
        'porcentaje': round(porcentaje, 2),
        'nivel_riesgo': nivel_riesgo,
        'clase': int(model.predict(X)[0]),
    }
