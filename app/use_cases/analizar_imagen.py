import io
import os
import cv2
import numpy as np
from ultralytics import YOLO
from app.core.database import supabase
from app.core.process import process_manager # Importamos el manager para guardar el frame

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

    def _procesar(self, imagen_bytes: bytes) -> list[tuple[str, float, float, float]]:
        """
        Ejecuta inferencia YOLO y devuelve una lista de (clasificación, confianza, centro X, centro Y).
        """
        if self._modelo is None:
            return []

        nparr = np.frombuffer(imagen_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Ejecutamos con un umbral base bajo de 0.45 para capturar todas las posibles detecciones
        results = self._modelo.predict(source=img, conf=0.45, verbose=False)
        

        if len(results) == 0 or len(results[0].boxes) == 0:
            return []

        detecciones = []
        for box in results[0].boxes:
            clase_id = int(box.cls[0])
            confianza = float(box.conf[0])
            nombre_clase = self._modelo.names[clase_id]

            # Filtro dinámico por clase para mejorar la precisión y evitar falsos positivos
            if nombre_clase.lower() == "defectuosa":
                if confianza < 0.68:  # Exigir confianza alta para clasificar como defectuosa
                    continue
            else:
                if confianza < 0.48:  # Confianza más permisiva para detectar los grados de madurez
                    continue

            x1, y1, x2, y2 = box.xyxy[0].tolist()
            centro_x = (x1 + x2) / 2
            centro_y = (y1 + y2) / 2
            
            detecciones.append((nombre_clase, confianza, centro_x, centro_y))
            
        return detecciones

    def execute(self, imagen_bytes: bytes) -> list[tuple[str, float, float, float]]:
        """
        Orquesta análisis YOLO y devuelve lista de detecciones.
        """
        return self._procesar(imagen_bytes)
