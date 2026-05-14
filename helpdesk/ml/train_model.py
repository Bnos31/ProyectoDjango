"""
train_model.py — Entrena el modelo RandomForest y guarda artefactos + métricas.
"""

import os
import json
import joblib
import pandas as pd
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    precision_score,
    recall_score,
    f1_score,
)

from helpdesk.ml.dataset import load_dataset

ML_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(ML_DIR, 'model.pkl')
ENCODERS_PATH = os.path.join(ML_DIR, 'encoders.pkl')
METADATA_PATH = os.path.join(ML_DIR, 'training_metadata.json')

CATEGORICAL_COLS = ['equipo', 'estado', 'tecnico_asignado']
FEATURE_COLS = ['equipo', 'estado', 'tecnico_asignado', 'mes_reporte', 'dia_semana', 'dias_resolucion']


def load_training_metadata():
    """Carga las métricas del último entrenamiento. Retorna None si no existe."""
    if not os.path.exists(METADATA_PATH):
        return None
    try:
        with open(METADATA_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def _save_training_metadata(accuracy, precision, recall, f1, num_records):
    metadata = {
        'fecha_entrenamiento': datetime.now().isoformat(),
        'accuracy': round(float(accuracy), 4),
        'precision': round(float(precision), 4),
        'recall': round(float(recall), 4),
        'f1': round(float(f1), 4),
        'num_records': int(num_records),
    }
    with open(METADATA_PATH, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
    return metadata


def train_model():
    """
    Carga el dataset, entrena un RandomForestClassifier y guarda el modelo.

    Returns:
        dict: Métricas de evaluación.
    """
    print("=" * 50)
    print("ENTRENAMIENTO DEL MODELO ML")
    print("=" * 50)

    print("\n[1/5] Cargando dataset desde Django ORM...")
    df = load_dataset()

    print("[2/5] Limpiando datos...")
    df = df.dropna(subset=FEATURE_COLS + ['falla_critica'])
    df['dias_resolucion'] = df['dias_resolucion'].fillna(-1)
    print(f"      Registros tras limpieza: {len(df)}")

    print("[3/5] Codificando variables categóricas...")
    encoders = {}
    df_encoded = df.copy()
    for col in CATEGORICAL_COLS:
        le = LabelEncoder()
        df_encoded[col] = le.fit_transform(df_encoded[col].astype(str))
        encoders[col] = le
        print(f"      '{col}': {list(le.classes_)}")

    print("[4/5] Dividiendo dataset (80% train / 20% test)...")
    X = df_encoded[FEATURE_COLS]
    y = df_encoded['falla_critica']
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"      Train: {len(X_train)} | Test: {len(X_test)}")

    print("[5/5] Entrenando RandomForestClassifier...")
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        class_weight='balanced',
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, average='weighted', zero_division=0)
    recall = recall_score(y_test, y_pred, average='weighted', zero_division=0)
    f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)
    report = classification_report(y_test, y_pred, target_names=['No Crítico', 'Crítico'])

    print("\n--- RESULTADOS ---")
    print(f"Accuracy:  {accuracy:.4f} ({accuracy*100:.2f}%)")
    print(f"Precision: {precision:.4f}")
    print(f"Recall:    {recall:.4f}")
    print(f"F1-score:  {f1:.4f}")
    print("\nReporte de clasificación:")
    print(report)

    joblib.dump(model, MODEL_PATH)
    joblib.dump(encoders, ENCODERS_PATH)

    metadata = _save_training_metadata(accuracy, precision, recall, f1, len(df))

    print(f"\nModelo guardado en:    {MODEL_PATH}")
    print(f"Encoders guardados en: {ENCODERS_PATH}")
    print(f"Metadata guardada en:  {METADATA_PATH}")
    print("=" * 50)

    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'report': report,
        'num_records': len(df),
        'model_path': MODEL_PATH,
    }


if __name__ == '__main__':
    train_model()
