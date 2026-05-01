import os
import sys
import subprocess
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Request
from app.core.process import process_manager
from app.core.config import settings

router = APIRouter()

@router.post("/analizar-imagen", status_code=202)
async def analizar_imagen(
    request: Request,
    background_tasks: BackgroundTasks,
    imagen: UploadFile = File(...),
):
    if not imagen.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo enviado no es una imagen válida.")
    
    imagen_bytes = await imagen.read()
    
    # Recuperamos el caso de uso desde el estado de la app
    analizador = request.app.state.analizador
    background_tasks.add_task(analizador.execute, imagen_bytes)
    
    return {"mensaje": "Imagen recibida. Análisis en proceso en background."}

@router.post("/iniciar-captura")
async def iniciar_captura():
    if process_manager.esta_activa():
        return {"mensaje": "La captura ya está en ejecución.", "pid": process_manager.proceso_captura.pid}

    # Subir 4 niveles desde app/api/v1/endpoints/ para llegar a app/
    _base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    script_path = os.path.join(_base_dir, "scripts", "captura_camara.py")

    log_file = open(settings.LOG_CAPTURA_PATH, "w", buffering=1, encoding="utf-8")
    proceso = subprocess.Popen(
        [sys.executable, "-u", script_path],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env={**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"},
    )
    process_manager.proceso_captura = proceso
    process_manager.log_file = log_file

    return {"mensaje": "Captura de cámara iniciada.", "pid": proceso.pid, "log": settings.LOG_CAPTURA_PATH}

@router.post("/detener-captura")
async def detener_captura():
    if not process_manager.esta_activa():
        return {"mensaje": "No hay ninguna captura activa."}
    
    pid = process_manager.proceso_captura.pid
    process_manager.detener_captura()
    return {"mensaje": "Captura detenida correctamente.", "pid": pid}

@router.get("/estado-captura")
async def estado_captura():
    """Consulta si el proceso de captura está corriendo."""
    activa = process_manager.esta_activa()
    pid = process_manager.proceso_captura.pid if activa else None
    return {"captura_activa": activa, "pid": pid}

@router.get("/logs-captura")
async def logs_captura(ultimas: int = 50):
    """Devuelve las últimas líneas del log del script de captura."""
    if not os.path.exists(settings.LOG_CAPTURA_PATH):
        return {"lineas": [], "info": "Aún no se ha iniciado ninguna captura."}
    
    with open(settings.LOG_CAPTURA_PATH, "r", encoding="utf-8") as f:
        lineas = f.readlines()
        
    return {
        "total_lineas": len(lineas),
        "mostrando_ultimas": min(ultimas, len(lineas)),
        "lineas": [l.rstrip() for l in lineas[-ultimas:]],
    }
