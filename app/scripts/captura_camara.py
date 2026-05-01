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
CAMERA_INDEX      = 0          # índice de cámara (0 = primera disponible)
JPEG_CALIDAD      = 85         # calidad JPEG para reducir payload


def _leer_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Captura imágenes y las envía a la API.")
    parser.add_argument("--url",       default=DEFAULT_URL,       help="URL base de la API")
    parser.add_argument("--intervalo", default=DEFAULT_INTERVALO, type=float,
                        help="Segundos entre capturas (default: 1)")
    return parser.parse_args()


def _enviar_imagen(api_url: str, imagen_bytes: bytes) -> None:
    """Envía los bytes de imagen al endpoint /analizar-imagen."""
    endpoint = f"{api_url.rstrip('/')}/captura/analizar-imagen"
    try:
        response = requests.post(
            endpoint,
            files={"imagen": ("captura.jpg", imagen_bytes, "image/jpeg")},
            timeout=5,
        )
        print(f"[OK] Enviada -> HTTP {response.status_code} | {response.text.strip()}")
    except requests.exceptions.ConnectionError:
        print(f"[WARN] No se pudo conectar con {endpoint}. Reintentando proxima vez.")
    except requests.exceptions.Timeout:
        print("[WARN] Timeout al enviar la imagen.")
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Error de red: {e}")


def _capturar_frame() -> bytes | None:
    """
    Intenta abrir la cámara, capturar un frame y devolverlo como bytes JPEG.
    Retorna None si la cámara no está disponible o el frame falla.
    """
    cap = cv2.VideoCapture(CAMERA_INDEX)
    try:
        if not cap.isOpened():
            return None

        ret, frame = cap.read()
        if not ret or frame is None:
            return None

        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_CALIDAD]
        success, buffer = cv2.imencode(".jpg", frame, encode_params)
        if not success:
            return None

        return buffer.tobytes()
    finally:
        cap.release()


def bucle_captura(api_url: str, intervalo: float) -> None:
    """
    Bucle principal: captura y envía indefinidamente.
    Nunca lanza excepción no controlada; siempre reintenta.
    """
    print(f"[START] Captura continua -> {api_url}/analizar-imagen")
    print(f"[INFO] Intervalo: {intervalo}s | Envia SIGTERM para detener.")

    while True:
        inicio = time.monotonic()

        try:
            imagen_bytes = _capturar_frame()

            if imagen_bytes is None:
                print("[WARN] Camara no disponible o frame invalido. Reintentando...")
            else:
                _enviar_imagen(api_url, imagen_bytes)

        except Exception as e:
            # Captura cualquier error inesperado para no romper el bucle
            print(f"[ERROR] Error inesperado: {e}")

        # Respetar el intervalo descontando el tiempo de procesamiento
        transcurrido = time.monotonic() - inicio
        pausa = max(0.0, intervalo - transcurrido)
        time.sleep(pausa)


if __name__ == "__main__":
    args = _leer_args()
    try:
        bucle_captura(api_url=args.url, intervalo=args.intervalo)
    except KeyboardInterrupt:
        print("[STOP] Captura detenida por el usuario.")
        sys.exit(0)
