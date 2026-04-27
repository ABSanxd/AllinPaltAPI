import io
import os
import numpy as np
from PIL import Image
import tf_keras  # Keras 2.x compatible con modelos Teachable Machine (.h5 de TF2)

# Labels según labels.txt:
# 0 -> Buen Estado  -> True
# 1 -> Defectuosas  -> False

MODEL_PATH  = os.path.join(os.path.dirname(__file__), "..", "modelo", "keras_model.h5")
LABELS_PATH = os.path.join(os.path.dirname(__file__), "..", "modelo", "labels.txt")

# Tamaño de entrada estándar de Teachable Machine
IMG_SIZE = (224, 224)


class AnalizarImagen:
    """
    Caso de uso: clasifica una imagen de palta usando el modelo
    entrenado con Teachable Machine.

    Uso:
        caso_uso = AnalizarImagen()
        resultado: bool = caso_uso.execute(imagen_bytes)

    Retorna:
        True  -> Buen Estado
        False -> Defectuosa
    """

    def __init__(self) -> None:
        self._modelo: tf_keras.Model = self._cargar_modelo()
        self._etiquetas = self._cargar_etiquetas()

    # ------------------------------------------------------------------
    # Métodos privados de orquestación
    # ------------------------------------------------------------------

    def _cargar_modelo(self) -> tf_keras.Model:
        """Carga el modelo .h5 desde disco (compatible con Teachable Machine / TF2)."""
        return tf_keras.models.load_model(MODEL_PATH, compile=False)

    def _cargar_etiquetas(self) -> dict[int, str]:
        """
        Lee labels.txt y devuelve un diccionario {índice: nombre_clase}.
        Formato esperado por Teachable Machine:
            0 Buen Estado
            1 Defectuosas
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
        Convierte los bytes de la imagen al tensor de entrada
        que espera el modelo de Teachable Machine:
        - Redimensiona a 224×224
        - Convierte a RGB
        - Normaliza píxeles al rango [-1, 1]
        - Añade la dimensión de batch
        """
        imagen = Image.open(io.BytesIO(imagen_bytes)).convert("RGB")
        imagen = imagen.resize(IMG_SIZE, Image.LANCZOS)
        array = np.asarray(imagen, dtype=np.float32)
        # Normalización Teachable Machine: (valor / 127.5) - 1
        array = (array / 127.5) - 1.0
        return np.expand_dims(array, axis=0)  # shape (1, 224, 224, 3)

    def _predecir(self, tensor: np.ndarray) -> int:
        """Realiza la inferencia y retorna el índice de la clase ganadora."""
        prediccion = self._modelo.predict(tensor, verbose=0)
        return int(np.argmax(prediccion[0]))

    def _interpretar(self, indice_clase: int) -> bool:
        """
        Mapea el índice de clase al resultado booleano.
        0 (Buen Estado)  -> True
        1 (Defectuosas)  -> False
        """
        nombre_clase = self._etiquetas.get(indice_clase, "Desconocido")
        return nombre_clase == "Buen Estado"

    # ------------------------------------------------------------------
    # Método público principal
    # ------------------------------------------------------------------

    def execute(self, imagen_bytes: bytes) -> bool:
        """
        Orquesta el análisis completo de la imagen.

        Args:
            imagen_bytes: contenido binario de la imagen recibida.

        Returns:
            True  si la palta está en Buen Estado.
            False si la palta está Defectuosa.
        """
        tensor      = self._preprocesar_imagen(imagen_bytes)
        indice      = self._predecir(tensor)
        resultado   = self._interpretar(indice)
        return resultado
