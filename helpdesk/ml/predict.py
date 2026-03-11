import os
import joblib
import pandas as pd

def predict_failure(equipo):
    """
    Analiza un equipo e infiere su probabilidad de falla crítica usando el modelo pre-entrenado.
    """
    model_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(model_dir, 'model.pkl')
    
    if not os.path.exists(model_path):
        return None  # El modelo no existe, falta entrenarlo
        
    # Cargar el modelo entrenado
    model = joblib.load(model_path)
    
    # Simular un caso base actual de este equipo para evaluar 
    # Mantenemos las mismas columnas que usamos en train_model.py
    data = {
        'equipo_nombre': [equipo.nombre],
        'estado': ['PENDIENTE'],  # Asumimos estado por defecto para inferir criticidad
        'tiene_tecnico': [0]      # Estado base sin asignar
    }
    
    df_input = pd.DataFrame(data)
    
    # Predecir probabilidades. Retorna arreglo de la forma [[prob_0, prob_1]]
    proba = model.predict_proba(df_input)
    
    # Validar qué clases aprendió el modelo durante el entrenamiento
    if len(model.classes_) == 2:
        # Extraemos la probabilidad de la clase 1 (Falla crítica)
        probabilidad = proba[0][1] * 100
    else:
        # Caso límite: el modelo se guardó con una sola clase
        clase = model.classes_[0]
        probabilidad = 100.0 if clase == 1 else 0.0
        
    return probabilidad
