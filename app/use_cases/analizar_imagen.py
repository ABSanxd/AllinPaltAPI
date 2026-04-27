import io
import os
import json
import threading
import datetime
import numpy as np
from PIL import Image
import tf_keras  # Keras 2.x — compatible con modelos Teachable Machine (.h5 de TF2)

# ── Rutas ────────────────────────────────────────────────────────────────────
_BASE = os.path.dirname(__file__)
MODEL_PATH      = os.path.join(_BASE, "..", "modelo", "keras_model.h5")
LABELS_PATH     = os.path.join(_BASE, "..", "modelo", "labels.txt")
RESULTADOS_PATH = os.path.join(_BASE, "..", "resultados.json")

# Tamaño de entrada estándar de Teachable Machine
IMG_SIZE = (224, 224)

# Lock para escritura concurrente en el JSON
_json_lock = threading.Lock()


class AnalizarImagen:
    """
    Caso de uso: clasifica una imagen de palta usando el modelo
    entrenado con Teachable Machine.

    Clasificaciones posibles:
        "Buen Estado"  → palta en buen estado
        "Defectuosas"  → palta defectuosa
        "Desconocido"  → objeto no reconocido (no es palta)

    Uso:
        caso_uso = AnalizarImagen()
        clasificacion: str = caso_uso.execute(imagen_bytes)
    """

    def __init__(self) -> None:
        self._modelo: tf_keras.Model = self._cargar_modelo()
        self._etiquetas: dict[int, str] = self._cargar_etiquetas()

    # ── Métodos privados ──────────────────────────────────────────────────────

    def _cargar_modelo(self) -> tf_keras.Model:
        """Carga el modelo .h5 desde disco (compatible con Teachable Machine / TF2)."""
        return tf_keras.models.load_model(MODEL_PATH, compile=False)

    def _cargar_etiquetas(self) -> dict[int, str]:
        """
        Lee labels.txt y devuelve {índice: nombre_clase}.
        Formato esperado:
            0 Buen Estado
            1 Defectuosas
            2 Desconocido
        """
        etiquetas: dict[int, str] = {}
        with open(LABELS_PATH, "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if not linea:
                    continue
                partes = linea.split(" ", 1)
                etiquetas[int(partes[0])] = partes[1]
        return etiquetas

    def _preprocesar_imagen(self, imagen_bytes: bytes) -> np.ndarray:
        """
        Convierte los bytes de la imagen al tensor de entrada:
        - Redimensiona a 224×224
        - Convierte a RGB
        - Normaliza píxeles al rango [-1, 1]  (estándar Teachable Machine)
        - Añade la dimensión de batch
        """
        imagen = Image.open(io.BytesIO(imagen_bytes)).convert("RGB")
        imagen = imagen.resize(IMG_SIZE, Image.LANCZOS)
        array  = np.asarray(imagen, dtype=np.float32)
        array  = (array / 127.5) - 1.0
        return np.expand_dims(array, axis=0)  # shape (1, 224, 224, 3)

    def _predecir(self, tensor: np.ndarray) -> int:
        """Ejecuta la inferencia y retorna el índice de la clase con mayor confianza."""
        prediccion = self._modelo.predict(tensor, verbose=0)
        return int(np.argmax(prediccion[0]))

    def _interpretar(self, indice_clase: int) -> str:
        """
        Mapea el índice a su etiqueta:
            0 → "Buen Estado"
            1 → "Defectuosas"
            2 → "Desconocido"
            * → "Desconocido"  (fallback)
        """
        return self._etiquetas.get(indice_clase, "Desconocido")

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
        Orquesta el análisis completo:
          1. Preprocesa la imagen.
          2. Ejecuta la inferencia.
          3. Interpreta el resultado.
          4. Guarda en resultados.json.

        Returns:
            "Buen Estado" | "Defectuosas" | "Desconocido"
        """
        tensor        = self._preprocesar_imagen(imagen_bytes)
        indice        = self._predecir(tensor)
        clasificacion = self._interpretar(indice)
        self._guardar_resultado(clasificacion)
        return clasificacion
