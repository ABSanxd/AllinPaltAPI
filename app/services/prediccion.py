from datetime import date
from pathlib import Path
from typing import Any, Optional

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor


BASE_DIR = Path(__file__).resolve().parents[2]
DATASET_PATH = BASE_DIR / "data" / "predicciones_entrenamiento.csv"
MODEL_DIR = BASE_DIR / "app" / "models"

MODELO_VIDA_PATH = MODEL_DIR / "modelo_vida_util.joblib"
MODELO_RIESGO_PATH = MODEL_DIR / "modelo_riesgo_deterioro.joblib"
MODELO_PRIORIDAD_PATH = MODEL_DIR / "modelo_prioridad_venta.joblib"

COLUMNAS_ENTRADA = [
    "temperatura_ambiente",
    "madurez_promedio",
    "dias_cosecha",
]


def calcular_dias_cosecha(fecha_cosecha: Optional[date]) -> int:
    if fecha_cosecha is None:
        return 0

    return max((date.today() - fecha_cosecha).days, 0)


def entrenar_modelos() -> None:
    """
    Entrena modelos Random Forest utilizando el dataset inicial.
    El dataset actual es sintético y debe ser reemplazado
    posteriormente por registros reales de lotes.
    """

    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"No se encontró el dataset de entrenamiento: {DATASET_PATH}"
        )

    df = pd.read_csv(DATASET_PATH)

    x = df[COLUMNAS_ENTRADA]
    y_vida = df["vida_util_estimada"]
    y_riesgo = df["riesgo_deterioro"]
    y_prioridad = df["prioridad_venta"]

    modelo_vida = RandomForestRegressor(
        n_estimators=100,
        random_state=42,
    )

    modelo_riesgo = RandomForestClassifier(
        n_estimators=100,
        random_state=42,
    )

    modelo_prioridad = RandomForestClassifier(
        n_estimators=100,
        random_state=42,
    )

    modelo_vida.fit(x, y_vida)
    modelo_riesgo.fit(x, y_riesgo)
    modelo_prioridad.fit(x, y_prioridad)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    joblib.dump(modelo_vida, MODELO_VIDA_PATH)
    joblib.dump(modelo_riesgo, MODELO_RIESGO_PATH)
    joblib.dump(modelo_prioridad, MODELO_PRIORIDAD_PATH)


def _cargar_modelos():
    modelos_existen = (
        MODELO_VIDA_PATH.exists()
        and MODELO_RIESGO_PATH.exists()
        and MODELO_PRIORIDAD_PATH.exists()
    )

    if not modelos_existen:
        entrenar_modelos()

    modelo_vida = joblib.load(MODELO_VIDA_PATH)
    modelo_riesgo = joblib.load(MODELO_RIESGO_PATH)
    modelo_prioridad = joblib.load(MODELO_PRIORIDAD_PATH)

    return modelo_vida, modelo_riesgo, modelo_prioridad


def calcular_prediccion(
    temperatura: float,
    madurez: float,
    dias_cosecha: int,
) -> dict[str, Any]:
    """
    Ejecuta predicción mediante algoritmos Random Forest.
    """

    if temperatura is None:
        raise ValueError("La temperatura es obligatoria.")

    if madurez is None:
        raise ValueError("La madurez promedio es obligatoria.")

    if not 1 <= float(madurez) <= 5:
        raise ValueError("La madurez promedio debe estar entre 1 y 5.")

    if int(dias_cosecha) < 0:
        raise ValueError("Los días desde cosecha no pueden ser negativos.")

    modelo_vida, modelo_riesgo, modelo_prioridad = _cargar_modelos()

    entrada = pd.DataFrame(
        [{
            "temperatura_ambiente": float(temperatura),
            "madurez_promedio": float(madurez),
            "dias_cosecha": int(dias_cosecha),
        }]
    )

    vida_util_estimada = modelo_vida.predict(entrada)[0]
    riesgo_deterioro = modelo_riesgo.predict(entrada)[0]
    prioridad_venta = modelo_prioridad.predict(entrada)[0]

    return {
        "vida_util_estimada": max(0, int(round(float(vida_util_estimada)))),
        "riesgo_deterioro": str(riesgo_deterioro),
        "prioridad_venta": str(prioridad_venta),
        "temperatura_usada": float(temperatura),
        "madurez_usada": float(madurez),
        "dias_cosecha": int(dias_cosecha),
        "algoritmo": "Random Forest",
        "dataset": "tecnico_parametrizado_postcosecha",
    }