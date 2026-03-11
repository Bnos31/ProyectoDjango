import os
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score

from .dataset import load_dataset

def train_model():
    """
    Carga el dataset, limpia datos, convierte categorías,
    entrena un RandomForestClassifier y guarda el modelo en model.pkl.
    """
    print("Iniciando módulo de Machine Learning...")
    print("1. Cargando dataset desde la base de datos...")
    df = load_dataset()
    
    if df.empty or len(df) < 5:
        print("ERROR: No hay suficientes datos para entrenar el modelo.")
        print("Registra al menos 5 incidencias (algunas con prioridad ALTA/CRITICA y otras BAJA/MEDIA).")
        return
        
    print(f"Dataset cargado con {len(df)} registros.")
    
    # Variables independientes (X) y objetivo (y)
    X = df[['equipo_nombre', 'estado', 'tiene_tecnico']]
    y = df['falla_critica']
    
    # Validar si solo hay una clase en el dataset (por ejemplo, puras fallas críticas)
    if len(y.unique()) < 2:
        print("ERROR: El modelo necesita ejemplos tanto de fallas críticas (1) como normales (0).")
        print("Actualmente solo hay registros de un tipo de falla en el sistema.")
        return
    
    print("2. Dividiendo datos de entrenamiento y prueba...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # 3. Pipeline para preprocesamiento y entrenamiento
    # Usamos ColumnTransformer para aplicar One-Hot-Encoding a variables textuales de manera segura
    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore'), ['equipo_nombre', 'estado'])
        ],
        remainder='passthrough'
    )
    
    # Usamos un RandomForestClassifier
    model = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', RandomForestClassifier(random_state=42, n_estimators=100))
    ])
    
    print("3. Entrenando el modelo RandomForestClassifier...")
    model.fit(X_train, y_train)
    
    # 4. Evaluación del modelo
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"4. Evaluación completada -> Precisión del modelo (Accuracy): {acc * 100:.2f}%")
    
    # 5. Guardar modelo con joblib
    model_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(model_dir, 'model.pkl')
    
    joblib.dump(model, model_path)
    print(f"5. ¡Exito! Modelo guardado en: {model_path}")
