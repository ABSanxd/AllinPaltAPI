"""
captura_camara.py
-----------------
Script autónomo que captura imágenes de la cámara conectada al dispositivo
y las envía al endpoint /analizar-imagen de la API.

Comportamiento (Multihilo):
  - Hilo Lector: Lee la cámara incesantemente para vaciar el buffer de OpenCV.
  - Hilo Principal: Despierta cada 1.5s, toma el cuadro más reciente y lo envía.
  - ThreadPool: Envía el POST HTTP asíncronamente para no bloquear el reloj.

Uso:
    python app/captura_camara.py
    python app/captura_camara.py --url http://127.0.0.1:8000 --intervalo 1
"""

import argparse
import sys
import time
import cv2
import requests
import threading
import os
from concurrent.futures import ThreadPoolExecutor

# ── Configuración por defecto ─────────────────────────────────────────────────
DEFAULT_URL       = "http://127.0.0.1:8000"
DEFAULT_INTERVALO = 1.5          # segundos entre capturas
JPEG_CALIDAD      = 60           # calidad JPEG reducida

# Leer la dirección de la cámara
_ENV_CAMARA = os.getenv("IP_CAMARA_CELULAR", "0")
try:
    CAMERA_INDEX = int(_ENV_CAMARA)
except ValueError:
    CAMERA_INDEX = _ENV_CAMARA

# Variables globales para Multithreading
frame_actual = None
lock_frame = threading.Lock()
camara_activa = True

def _leer_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Captura imágenes y las envía a la API.")
    parser.add_argument("--url",       default=DEFAULT_URL,       help="URL base de la API")
    parser.add_argument("--intervalo", default=DEFAULT_INTERVALO, type=float,
                        help="Segundos entre capturas (default: 1.5)")
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


def _hilo_consumidor_camara(cap: cv2.VideoCapture):
    """
    Hilo en segundo plano que lee la cámara sin pausas para vaciar el buffer de OpenCV.
    Guarda solo el frame más reciente comprimido en la variable global.
    """
    global frame_actual, camara_activa
    while camara_activa:
        if not cap.isOpened():
            time.sleep(0.1)
            continue

        ret, frame = cap.read()
        if ret and frame is not None:
            # Redimensionar y comprimir en el hilo secundario para liberar al principal
            h, w = frame.shape[:2]
            if w > 640 or h > 480:
                frame = cv2.resize(frame, (640, 480), interpolation=cv2.INTER_AREA)

            encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_CALIDAD]
            success, buffer = cv2.imencode(".jpg", frame, encode_params)
            
            if success:
                # Guardamos el frame de forma segura
                with lock_frame:
                    frame_actual = buffer.tobytes()
        else:
            # Si hay error temporal de la cámara, pausamos ligeramente
            time.sleep(0.05)


def bucle_captura(api_url: str, intervalo: float, lote_id: str) -> None:
    """
    Bucle principal: extrae el último frame del hilo lector y lo envía.
    """
    global frame_actual, camara_activa
    print(f"[START] Captura continua (Multihilo) -> {api_url}/analizar-imagen")
    print(f"[INFO] Lote ID: {lote_id} | Intervalo: {intervalo}s")

    cap = cv2.VideoCapture(CAMERA_INDEX)
    time.sleep(0.5)

    # Iniciar el hilo que consume la cámara
    lector_thread = threading.Thread(target=_hilo_consumidor_camara, args=(cap,), daemon=True)
    lector_thread.start()

    # Pool para enviar peticiones HTTP sin bloquear el reloj
    executor = ThreadPoolExecutor(max_workers=3)

    try:
        while True:
            inicio = time.monotonic()

            if not cap.isOpened():
                print("[WARN] Intentando reabrir cámara...")
                cap.open(CAMERA_INDEX)
                time.sleep(0.5)

            # Tomar la foto más fresca
            bytes_a_enviar = None
            with lock_frame:
                if frame_actual is not None:
                    bytes_a_enviar = frame_actual
                    frame_actual = None # Limpiamos para no reenviar duplicados si la cámara se congela
            
            if bytes_a_enviar is None:
                print("[WARN] No hay frame fresco de la cámara. Reintentando...")
            else:
                # Enviar de forma asíncrona
                executor.submit(_enviar_imagen, api_url, bytes_a_enviar, lote_id)

            # Respetar el intervalo estrictamente
            transcurrido = time.monotonic() - inicio
            pausa = max(0.0, intervalo - transcurrido)
            time.sleep(pausa)

    except Exception as e:
        print(f"[ERROR] Error inesperado en el bucle principal: {e}")
    finally:
        print("[INFO] Deteniendo hilos y liberando cámara...")
        camara_activa = False
        executor.shutdown(wait=False)
        cap.release()


if __name__ == "__main__":
    args = _leer_args()
    try:
        bucle_captura(api_url=args.url, intervalo=args.intervalo, lote_id=args.lote_id)
    except KeyboardInterrupt:
        print("[STOP] Captura detenida por el usuario.")
        sys.exit(0)
