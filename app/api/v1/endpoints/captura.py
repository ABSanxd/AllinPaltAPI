import os
import sys
import subprocess

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Request, Form

from app.core.process import process_manager
from app.core.config import settings
from app.core.database import supabase

router = APIRouter()

@router.post("/analizar-imagen", status_code=202)
async def analizar_imagen(
    request: Request,
    background_tasks: BackgroundTasks,
    imagen: UploadFile = File(...),
    lote_id: str = Form(...),
):
    if not imagen.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo enviado no es una imagen válida.")
    
    imagen_bytes = await imagen.read()
    
    analizador = request.app.state.analizador
    
    def procesar_y_contar(img_bytes):
        clasificacion, confianza = analizador.execute(img_bytes)
        
        process_manager.total_paltas += 1
        process_manager.suma_confianza += confianza
        
        if clasificacion.lower() == "defectuosa":
            process_manager.cant_defectuosas += 1
        else:
            process_manager.cant_buenas += 1
            if "madurez" in clasificacion.lower():
                try:
                    nivel = int(clasificacion.split("_")[-1])
                    process_manager.suma_madurez += nivel
                    process_manager.conteo_madurez += 1
                except:
                    pass

    background_tasks.add_task(procesar_y_contar, imagen_bytes)
    
    return {
        "mensaje": "Imagen recibida. Análisis en proceso en memoria.",
        "lote_id": lote_id
    }

@router.post("/iniciar-captura")
async def iniciar_captura(lote_id: str):
    if process_manager.esta_activa():
        return {"mensaje": "La captura ya está en ejecución.", "pid": process_manager.proceso_captura.pid}

    # Resetear contadores en memoria al iniciar un nuevo proceso
    process_manager.reset_contadores()
    process_manager.lote_id_activo = lote_id

    # ACTUALIZAR EN SUPABASE: Estado y Fecha de Inicio
    from app.schemas.enums import EstadoLote
    from datetime import datetime
    supabase.table("lotes").update({
        "estado": EstadoLote.EN_PROCESO.value,
        "fecha_inicio_procesamiento": datetime.now().isoformat()
    }).eq("id", lote_id).execute()

    # Subir 4 niveles desde app/api/v1/endpoints/ para llegar a app/
    _base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    script_path = os.path.join(_base_dir, "scripts", "captura_camara.py")

    log_file = open(settings.LOG_CAPTURA_PATH, "w", buffering=1, encoding="utf-8")
    proceso = subprocess.Popen(
        [sys.executable, "-u", script_path, "--lote_id", lote_id],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env={**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8"},
    )
    process_manager.proceso_captura = proceso
    process_manager.log_file = log_file
    process_manager.lote_id_activo = lote_id  # Guardamos el ID del lote para el cierre

    return {"mensaje": "Captura de cámara iniciada.", "pid": proceso.pid, "log": settings.LOG_CAPTURA_PATH}

@router.post("/detener-captura")
async def detener_captura():
    if not process_manager.esta_activa():
        return {"mensaje": "No hay ninguna captura activa."}
    
    pid = process_manager.proceso_captura.pid
    lote_id = process_manager.lote_id_activo
    
    # 1. Detener el proceso físico
    process_manager.detener_captura()

    # 2. Calcular resumen final desde los contadores en memoria
    total = process_manager.total_paltas
    buenas = process_manager.cant_buenas
    malas = process_manager.cant_defectuosas
    conf_promedio = (process_manager.suma_confianza / total) if total > 0 else 0
    madurez_promedio = (process_manager.suma_madurez / process_manager.conteo_madurez) if process_manager.conteo_madurez > 0 else 0
    
    # 3. Guardar en deteccion_resumen (UNA SOLA VEZ)
    resumen_data = {
        "lote_id": lote_id,
        "total_paltas": total,
        "cant_buenas": buenas,
        "cant_defectuosas": malas,
        "porcentaje_buenas": (buenas / total * 100) if total > 0 else 0,
        "porcentaje_defectuosas": (malas / total * 100) if total > 0 else 0,
        "madurez_promedio": madurez_promedio,
        "confianza_avg": conf_promedio,
        "finalizado_en": __import__('datetime').datetime.now().isoformat()
    }
    supabase.table("deteccion_resumen").insert(resumen_data).execute()

    # 4. Finalizar el lote
    from app.schemas.enums import EstadoLote
    supabase.table("lotes").update({"estado": EstadoLote.FINALIZADO.value}).eq("id", lote_id).execute()
    
    process_manager.lote_id_activo = None
    
    return {"mensaje": "Captura detenida y resumen generado correctamente.", "pid": pid}

@router.get("/monitor/{lote_id}")
async def monitor_lote(lote_id: str, ultimas_lineas: int = 10):
    """
    Endpoint unificado (Maestro) para el Dashboard.
    Devuelve conteos en memoria, estado del proceso y logs en una sola llamada.
    """
    # 1. Estado y Conteos
    activa = process_manager.esta_activa()
    
    resumen = {
        "total_paltas": 0,
        "cant_buenas": 0,
        "cant_defectuosas": 0
    }
    
    if process_manager.lote_id_activo == lote_id:
        resumen = {
            "total_paltas": process_manager.total_paltas,
            "cant_buenas": process_manager.cant_buenas,
            "cant_defectuosas": process_manager.cant_defectuosas
        }

    # 2. Logs
    lineas_log = []
    if os.path.exists(settings.LOG_CAPTURA_PATH):
        try:
            with open(settings.LOG_CAPTURA_PATH, "r", encoding="utf-8") as f:
                lineas_log = [l.rstrip() for l in f.readlines()[-ultimas_lineas:]]
        except:
            pass

    return {
        "captura_activa": activa,
        "resumen": resumen,
        "logs": lineas_log,
        "lote_id": lote_id
    }

@router.get("/")
async def root_captura():
    return {"mensaje": "Módulo de captura activo"}
