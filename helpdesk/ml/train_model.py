"""
train_model.py — Entrena el modelo RandomForest y lo guarda en model.pkl.

Uso desde Django shell:
    python manage.py shell
    from helpdesk.ml.train_model import train_model
    train_model()

Esto genera:
    helpdesk/ml/model.pkl
    helpdesk/ml/encoders.pkl
"""

import os
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report

from helpdesk.ml.dataset import load_dataset


# Directorio donde se guardan los artefactos del modelo
ML_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(ML_DIR, 'model.pkl')
ENCODERS_PATH = os.path.join(ML_DIR, 'encoders.pkl')

# Columnas categóricas que necesitan codificación
CATEGORICAL_COLS = ['equipo', 'estado', 'tecnico_asignado']

# Features usadas para entrenar (NO incluye 'falla_critica' que es el target)
FEATURE_COLS = ['equipo', 'estado', 'tecnico_asignado', 'mes_reporte', 'dia_semana', 'dias_resolucion']


def train_model():
    """
    Carga el dataset, entrena un RandomForestClassifier y guarda el modelo.

    Returns:
        dict: Métricas de evaluación (accuracy, reporte de clasificación).
    """
    print("=" * 50)
    print("ENTRENAMIENTO DEL MODELO ML")
    print("=" * 50)

    # 1. Cargar dataset
    print("\n[1/5] Cargando dataset desde Django ORM...")
    df = load_dataset()

    # 2. Limpiar datos
    print("[2/5] Limpiando datos...")
    df = df.dropna(subset=FEATURE_COLS + ['falla_critica'])
    df['dias_resolucion'] = df['dias_resolucion'].fillna(-1)
    print(f"      Registros tras limpieza: {len(df)}")

    # 3. Codificar variables categóricas con LabelEncoder
    print("[3/5] Codificando variables categóricas...")
    encoders = {}
    df_encoded = df.copy()

    for col in CATEGORICAL_COLS:
        le = LabelEncoder()
        df_encoded[col] = le.fit_transform(df_encoded[col].astype(str))
        encoders[col] = le
        print(f"      '{col}': {list(le.classes_)}")

    # 4. Dividir en entrenamiento y prueba (80/20)
    print("[4/5] Dividiendo dataset (80% train / 20% test)...")
    X = df_encoded[FEATURE_COLS]
    y = df_encoded['falla_critica']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"      Train: {len(X_train)} | Test: {len(X_test)}")

    # 5. Entrenar RandomForestClassifier
    print("[5/5] Entrenando RandomForestClassifier...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        class_weight='balanced',  # Compensa si hay desbalance de clases
    )
    model.fit(X_train, y_train)

    # Evaluación
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, target_names=['No Crítico', 'Crítico'])

    print("\n--- RESULTADOS ---")
    print(f"Accuracy: {accuracy:.4f} ({accuracy*100:.2f}%)")
    print("\nReporte de clasificación:")
    print(report)

    # Guardar modelo y encoders
    joblib.dump(model, MODEL_PATH)
    joblib.dump(encoders, ENCODERS_PATH)
    print(f"\nModelo guardado en:    {MODEL_PATH}")
    print(f"Encoders guardados en: {ENCODERS_PATH}")
    print("=" * 50)

    return {
        'accuracy': accuracy,
        'report': report,
        'model_path': MODEL_PATH,
    }


if __name__ == '__main__':
    train_model()
