import io
import os
import cv2
import numpy as np
from ultralytics import YOLO
from app.core.database import supabase

_BASE = os.path.dirname(__file__)
MODEL_PATH = os.path.join(_BASE, "..", "ml_models", "best.pt")


class AnalizarImagen:
    """
    Caso de uso: detecta y clasifica paltas usando YOLO.
    Guarda el resultado en Supabase.
    """

    def __init__(self) -> None:
        self._modelo = self._cargar_modelo()

    def _cargar_modelo(self):
        """Carga el modelo .pt de YOLO."""
        if not os.path.exists(MODEL_PATH):
            print(f"ADVERTENCIA: No se encontró el modelo en {MODEL_PATH}")
            return None
        return YOLO(MODEL_PATH)

    def _procesar(self, imagen_bytes: bytes) -> tuple[str, float]:
        """
        Ejecuta inferencia YOLO y devuelve clasificación + confianza.
        """
        if self._modelo is None:
            return "Error: Modelo no cargado", 0.0

        nparr = np.frombuffer(imagen_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        results = self._modelo.predict(source=img, conf=0.25, verbose=False)

        if len(results) == 0 or len(results[0].boxes) == 0:
            return "Desconocido", 0.0

        primera_deteccion = results[0].boxes[0]
        clase_id = int(primera_deteccion.cls[0])
        confianza = float(primera_deteccion.conf[0])
        nombre_clase = self._modelo.names[clase_id]

        return nombre_clase, confianza

    def execute(self, imagen_bytes: bytes) -> tuple[str, float]:
        """
        Orquesta análisis YOLO y devuelve el resultado.
        """
        clasificacion, confianza = self._procesar(imagen_bytes)
        return clasificacion, confianza
