import io
import os
import json
import threading
import datetime
import cv2
import numpy as np
from PIL import Image
from ultralytics import YOLO

# ── Rutas ────────────────────────────────────────────────────────────────────
_BASE = os.path.dirname(__file__)
# Usaremos best.pt que es el nombre estándar de exportación de Roboflow/YOLO
MODEL_PATH      = os.path.join(_BASE, "..", "ml_models", "best.pt")
RESULTADOS_PATH = os.path.join(_BASE, "..", "..", "resultados.json")

# Lock para escritura concurrente en el JSON
_json_lock = threading.Lock()


class AnalizarImagen:
    """
    Caso de uso: detecta y clasifica paltas usando YOLOv11.
    Migrado de Teachable Machine (Keras) a Ultralytics.
    """

    def __init__(self) -> None:
        self._modelo = self._cargar_modelo()

    # ── Métodos privados ──────────────────────────────────────────────────────

    def _cargar_modelo(self):
        """Carga el modelo .pt de YOLO."""
        if not os.path.exists(MODEL_PATH):
            print(f"⚠️  ADVERTENCIA: No se encontró el modelo en {MODEL_PATH}")
            return None
        return YOLO(MODEL_PATH)

    def _procesar(self, imagen_bytes: bytes):
        """
        Ejecuta la inferencia de YOLO sobre los bytes de la imagen.
        """
        if self._modelo is None:
            return "Error: Modelo no cargado"

        # Convertir bytes a imagen de OpenCV
        nparr = np.frombuffer(imagen_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Ejecutar predicción
        # Bajamos conf a 0.25 para que sea más fácil detectar en pruebas
        results = self._modelo.predict(source=img, conf=0.25, verbose=False)
        
        if len(results) == 0 or len(results[0].boxes) == 0:
            return "Desconocido"

        # Obtenemos la clase con mayor confianza de la primera detección
        primera_deteccion = results[0].boxes[0]
        clase_id = int(primera_deteccion.cls[0])
        nombre_clase = self._modelo.names[clase_id]

        return nombre_clase

    def _guardar_resultado(self, clasificacion: str) -> dict:
        """
        Persiste en resultados.json la clasificación junto al timestamp.
        Usa un lock para evitar condiciones de carrera en escrituras concurrentes.
        """
        registro = {
            "timestamp":     datetime.datetime.now().isoformat(),
            "clasificacion": clasificacion,
        }

        with _json_lock:
            # Leer registros existentes
            if os.path.exists(RESULTADOS_PATH):
                try:
                    with open(RESULTADOS_PATH, "r", encoding="utf-8") as f:
                        resultados: list = json.load(f)
                except (json.JSONDecodeError, OSError):
                    resultados = []
            else:
                resultados = []

            resultados.append(registro)

            with open(RESULTADOS_PATH, "w", encoding="utf-8") as f:
                json.dump(resultados, f, ensure_ascii=False, indent=2)

        return registro

    # ── Método público ────────────────────────────────────────────────────────

    def execute(self, imagen_bytes: bytes) -> str:
        """
        Orquesta el análisis con YOLO.
        """
        clasificacion = self._procesar(imagen_bytes)
        self._guardar_resultado(clasificacion)
        return clasificacion
