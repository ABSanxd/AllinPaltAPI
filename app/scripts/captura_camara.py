"""
captura_camara.py
-----------------
Script autónomo que captura imágenes de la cámara conectada al dispositivo
y las envía al endpoint /analizar-imagen de la API.

Comportamiento:
  - Bucle infinito (while True): nunca se detiene salvo CTRL+C o señal de término.
  - 1 imagen por segundo.
  - Si no encuentra cámara, sigue reintentando indefinidamente.
  - Cada imagen capturada se envía al endpoint como multipart/form-data.

Uso:
    python app/captura_camara.py
    python app/captura_camara.py --url http://127.0.0.1:8000 --intervalo 1
"""

import argparse
import sys
import time
import cv2
import requests

# ── Configuración por defecto ─────────────────────────────────────────────────
DEFAULT_URL       = "http://127.0.0.1:8000"
DEFAULT_INTERVALO = 1          # segundos entre capturas
JPEG_CALIDAD      = 60         # calidad JPEG reducida para optimizar peso y velocidad

# Leer la dirección de la cámara desde las variables de entorno pasadas por la API
import os
_ENV_CAMARA = os.getenv("IP_CAMARA_CELULAR", "0")
try:
    CAMERA_INDEX = int(_ENV_CAMARA)
except ValueError:
    CAMERA_INDEX = _ENV_CAMARA


def _leer_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Captura imágenes y las envía a la API.")
    parser.add_argument("--url",       default=DEFAULT_URL,       help="URL base de la API")
    parser.add_argument("--intervalo", default=DEFAULT_INTERVALO, type=float,
                        help="Segundos entre capturas (default: 1)")
    parser.add_argument("--lote_id",   required=True,             help="ID del lote activo en Supabase")
    return parser.parse_args()


def _enviar_imagen(api_url: str, imagen_bytes: bytes, lote_id: str) -> None:
    """Envía los bytes de imagen al endpoint /analizar-imagen."""
    endpoint = f"{api_url.rstrip('/')}/api/v1/captura/analizar-imagen"
    try:
        response = requests.post(
            endpoint,
            files={"imagen": ("captura.jpg", imagen_bytes, "image/jpeg")},
            data={"lote_id": lote_id},
            timeout=5,
        )
        print(f"[OK] Enviada -> HTTP {response.status_code} | {response.text.strip()}")
    except requests.exceptions.ConnectionError:
        print(f"[WARN] No se pudo conectar con {endpoint}. Reintentando proxima vez.")
    except requests.exceptions.Timeout:
        print("[WARN] Timeout al enviar la imagen.")
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error de red: {e}")


def _capturar_frame(cap: cv2.VideoCapture) -> bytes | None:
    """
    Lee un frame de la cámara ya abierta, lo redimensiona a 640x480 y lo devuelve en bytes JPEG.
    """
    if not cap.isOpened():
        return None

    ret, frame = cap.read()
    if not ret or frame is None:
        return None

    # Redimensionar el frame a 640x480 para aligerar la transmisión y el modelo YOLO
    h, w = frame.shape[:2]
    if w > 640 or h > 480:
        frame = cv2.resize(frame, (640, 480), interpolation=cv2.INTER_AREA)

    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_CALIDAD]
    success, buffer = cv2.imencode(".jpg", frame, encode_params)
    if not success:
        return None

    return buffer.tobytes()


def bucle_captura(api_url: str, intervalo: float, lote_id: str) -> None:
    """
    Bucle principal: mantiene abierta la cámara y captura periódicamente.
    """
    print(f"[START] Captura continua -> {api_url}/analizar-imagen")
    print(f"[INFO] Lote ID: {lote_id} | Intervalo: {intervalo}s")

    cap = cv2.VideoCapture(CAMERA_INDEX)
    try:
        # Dar un breve respiro para inicialización de hardware en Windows
        time.sleep(0.5)

        while True:
            inicio = time.monotonic()

            try:
                if not cap.isOpened():
                    print("[WARN] Intentando reabrir cámara...")
                    cap.open(CAMERA_INDEX)
                    time.sleep(0.5)

                imagen_bytes = _capturar_frame(cap)

                if imagen_bytes is None:
                    print("[WARN] Camara no disponible o frame invalido. Reintentando...")
                else:
                    _enviar_imagen(api_url, imagen_bytes, lote_id)

            except Exception as e:
                print(f"[ERROR] Error inesperado en el bucle: {e}")

            # Respetar el intervalo descontando el tiempo de procesamiento
            transcurrido = time.monotonic() - inicio
            pausa = max(0.0, intervalo - transcurrido)
            time.sleep(pausa)

    finally:
        print("[INFO] Liberando cámara...")
        cap.release()


if __name__ == "__main__":
    args = _leer_args()
    try:
        bucle_captura(api_url=args.url, intervalo=args.intervalo, lote_id=args.lote_id)
    except KeyboardInterrupt:
        print("[STOP] Captura detenida por el usuario.")
        sys.exit(0)
