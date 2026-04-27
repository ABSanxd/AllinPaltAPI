import os
import sys
import logging
import subprocess
from contextlib import asynccontextmanager

# ── Rutas de archivos de datos ────────────────────────────────────────────────
_ROOT         = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_CAPTURA   = os.path.join(_ROOT, "captura_camara.log")

# Suprimir logs verbosos de TensorFlow ANTES de importar keras/tf
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
logging.getLogger("tensorflow").setLevel(logging.ERROR)
logging.getLogger("absl").setLevel(logging.ERROR)

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks

from app.use_cases.analizar_imagen import AnalizarImagen

# ── Estado global del servidor ────────────────────────────────────────────────
_state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Carga el modelo una sola vez al iniciar el servidor."""
    print("🥑  Cargando modelo de clasificación de paltas...")
    _state["analizar_imagen"]   = AnalizarImagen()
    _state["proceso_captura"]   = None   # subprocess de captura_camara.py
    _state["log_file"]           = None   # handle del archivo de log
    print("✅  Modelo cargado. Servidor listo.")
    yield
    # ── Limpieza al apagar ────────────────────────────────────────────────────
    _detener_proceso_captura()
    _state.clear()


# ── Helpers de proceso ────────────────────────────────────────────────────────

def _captura_activa() -> bool:
    """Devuelve True si el proceso de captura está corriendo."""
    proc: subprocess.Popen | None = _state.get("proceso_captura")
    return proc is not None and proc.poll() is None


def _detener_proceso_captura() -> None:
    """Termina el proceso de captura y cierra el archivo de log."""
    proc: subprocess.Popen | None = _state.get("proceso_captura")
    if proc is not None and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    _state["proceso_captura"] = None
    # Cerrar el handle del log si está abierto
    lf = _state.get("log_file")
    if lf and not lf.closed:
        lf.close()
    _state["log_file"] = None


# ── Tarea de análisis (background) ────────────────────────────────────────────

def _tarea_analizar(imagen_bytes: bytes) -> None:
    """
    Se ejecuta en background thread:
      1. Corre la inferencia del modelo.
      2. Guarda el resultado en resultados.json.
    """
    caso_uso: AnalizarImagen = _state["analizar_imagen"]
    caso_uso.execute(imagen_bytes)


# ── Aplicación FastAPI ────────────────────────────────────────────────────────

app = FastAPI(
    title="AllinPalt API",
    description="API para análisis de paltas usando visión por computadora.",
    version="2.0.0",
    lifespan=lifespan,
)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "AllinPalt API activa 🥑"}


@app.post("/analizar-imagen", status_code=202)
async def analizar_imagen(
    background_tasks: BackgroundTasks,
    imagen: UploadFile = File(...),
):
    """
    Recibe una imagen de palta y la analiza **en background**.

    - Retorna **202 Accepted** inmediatamente para no bloquear al cliente.
    - El resultado (clasificación + timestamp) se persiste en `resultados.json`.

    Clasificaciones posibles:
    - `Buen Estado`
    - `Defectuosas`
    - `Desconocido`
    """
    if not imagen.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="El archivo enviado no es una imagen válida.",
        )

    imagen_bytes = await imagen.read()
    background_tasks.add_task(_tarea_analizar, imagen_bytes)

    return {"mensaje": "Imagen recibida. Análisis en proceso en background."}


@app.post("/iniciar-captura")
async def iniciar_captura():
    """
    Inicia el script `captura_camara.py` como proceso independiente.

    - Si ya hay una captura activa, lo informa sin iniciar otra.
    - El script captura 1 imagen por segundo y la envía a `/analizar-imagen`.
    """
    if _captura_activa():
        pid = _state["proceso_captura"].pid
        return {"mensaje": f"La captura ya está en ejecución.", "pid": pid}

    script_path = os.path.join(os.path.dirname(__file__), "captura_camara.py")

    # ── Abrir archivo de log (line-buffered) ─────────────────────────────────
    # NO usar subprocess.PIPE: si nadie lee la pipe el buffer del SO se llena
    # y el subprocess se bloquea. Un archivo de log nunca se bloquea.
    log_file = open(LOG_CAPTURA, "w", buffering=1, encoding="utf-8")

    proceso = subprocess.Popen(
        [sys.executable, "-u", script_path],  # -u = salida sin buffer
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env={**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"},
    )
    _state["proceso_captura"] = proceso
    _state["log_file"]        = log_file

    return {
        "mensaje": "Captura de cámara iniciada.",
        "pid": proceso.pid,
        "log": LOG_CAPTURA,
    }


@app.post("/detener-captura")
async def detener_captura():
    """
    Detiene el proceso de captura de cámara si está activo.
    """
    if not _captura_activa():
        return {"mensaje": "No hay ninguna captura activa."}

    pid = _state["proceso_captura"].pid
    _detener_proceso_captura()

    return {
        "mensaje": "Captura detenida correctamente.",
        "pid": pid,
    }


@app.get("/estado-captura")
async def estado_captura():
    """Consulta si el proceso de captura está corriendo."""
    activa = _captura_activa()
    pid    = _state["proceso_captura"].pid if activa else None
    return {"captura_activa": activa, "pid": pid}


@app.get("/logs-captura")
async def logs_captura(ultimas: int = 50):
    """
    Devuelve las últimas líneas del log del script de captura.
    Útil para depurar si la cámara está funcionando o hay errores.

    - **ultimas**: cuántas líneas mostrar (default 50)
    """
    if not os.path.exists(LOG_CAPTURA):
        return {"lineas": [], "info": "Aún no se ha iniciado ninguna captura."}

    with open(LOG_CAPTURA, "r", encoding="utf-8") as f:
        lineas = f.readlines()

    return {
        "total_lineas": len(lineas),
        "mostrando_ultimas": min(ultimas, len(lineas)),
        "lineas": [l.rstrip() for l in lineas[-ultimas:]],
    }