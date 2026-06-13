import os
import sys
import subprocess
import asyncio
import time
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, HTTPException, Request, Form, BackgroundTasks
from fastapi.responses import StreamingResponse
from app.core.process import process_manager
from app.core.config import settings
from app.core.database import supabase
from app.schemas.enums import EstadoLote
from app.services.clima import obtener_clima_futuro

router = APIRouter()

# Variable global en la RAM para almacenar el último frame que llega de la cámara
ultimo_frame_procesado = None

@router.post("/analizar-imagen", status_code=202)
async def analizar_imagen(
    request: Request,
    background_tasks: BackgroundTasks,
    imagen: UploadFile = File(...),
    lote_id: str = Form(...),
):
    global ultimo_frame_procesado
    if not imagen.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="El archivo enviado no es una imagen válida.")

    imagen_bytes = await imagen.read()
    analizador = request.app.state.analizador

    # Auxiliares de tracking
    def distancia(p1, p2):
        return ((p1["x"] - p2["x"]) ** 2 + (p1["y"] - p2["y"]) ** 2) ** 0.5

    def obtener_nivel_madurez(clasificacion: str):
        texto = clasificacion.lower()
        if "madurez" not in texto:
            return None
        try:
            return int(texto.split("_")[-1])
        except:
            return None

    def procesar_y_contar(img_bytes):
        global ultimo_frame_procesado
        # Ejecutar inferencia de YOLO asíncronamente
        detecciones = analizador.execute(img_bytes)
        
        # GUARDAR EL FRAME EN MEMORIA
        ultimo_frame_procesado = img_bytes 
        
        if not detecciones:
            process_manager.posiciones_frame_anterior = []
        else:
            nuevas_posiciones = []
            tolerancia = 40  

            for nombre_clase, confianza, centro_x, centro_y in detecciones:
                posicion_actual = {"x": centro_x, "y": centro_y, "clase": nombre_clase}
                
                duplicada_mismo_frame = any(
                    distancia(posicion_actual, pos_nueva) <= tolerancia
                    for pos_nueva in nuevas_posiciones
                )
                if duplicada_mismo_frame:
                    continue 
                    
                nuevas_posiciones.append(posicion_actual)

                # Se considera ya contada solo si está en la misma posición Y tiene la misma clasificación/madurez
                ya_contada = any(
                    distancia(posicion_actual, pos_anterior) <= tolerancia and posicion_actual["clase"] == pos_anterior.get("clase")
                    for pos_anterior in process_manager.posiciones_frame_anterior
                )

                if not ya_contada:
                    process_manager.total_paltas += 1
                    process_manager.suma_confianza += confianza

                    if nombre_clase.lower() == "defectuosa":
                        process_manager.cant_defectuosas += 1
                    else:
                        process_manager.cant_buenas += 1
                        nivel = obtener_nivel_madurez(nombre_clase)
                        if nivel is not None:
                            process_manager.suma_madurez += nivel
                            process_manager.conteo_madurez += 1
                            key = f"m{nivel}"
                            process_manager.conteo_niveles[key] = process_manager.conteo_niveles.get(key, 0) + 1

            process_manager.posiciones_frame_anterior = nuevas_posiciones

    background_tasks.add_task(procesar_y_contar, imagen_bytes)

    return {
        "status": "procesando",
        "lote_id": lote_id
    }

@router.post("/iniciar-captura")
async def iniciar_captura(lote_id: str):
    global ultimo_frame_procesado
    if process_manager.esta_activa():
        return {"mensaje": "La captura ya está en ejecución.", "pid": process_manager.proceso_captura.pid}

    process_manager.reset_contadores()
    process_manager.lote_id_activo = lote_id
    ultimo_frame_procesado = None  # Limpiar residuos del lote anterior

    supabase.table("lotes").update({
        "estado": EstadoLote.EN_PROCESO.value,
        "fecha_inicio_procesamiento": datetime.now().isoformat()
    }).eq("id", lote_id).execute()

    _base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    script_path = os.path.join(_base_dir, "scripts", "captura_camara.py")

    log_file = open(settings.LOG_CAPTURA_PATH, "w", buffering=1, encoding="utf-8")
    proceso = subprocess.Popen(
        [sys.executable, "-u", script_path, "--lote_id", lote_id],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env={**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8", "IP_CAMARA_CELULAR": settings.IP_CAMARA_CELULAR},
    )
    process_manager.proceso_captura = proceso
    process_manager.log_file = log_file

    return {"mensaje": "Captura de cámara iniciada.", "pid": proceso.pid, "log": settings.LOG_CAPTURA_PATH}

@router.post("/detener-captura")
async def detener_captura():
    global ultimo_frame_procesado
    if not process_manager.esta_activa():
        return {"mensaje": "No hay ninguna captura activa."}
    
    pid = process_manager.proceso_captura.pid
    lote_id = process_manager.lote_id_activo
    
    # 1. Matar el proceso de la cámara primero para detener las ráfagas de POSTs
    process_manager.detener_captura()
    ultimo_frame_procesado = None 

    # 2. Cálculos finales
    total = process_manager.total_paltas
    buenas = process_manager.cant_buenas
    malas = process_manager.cant_defectuosas
    conf_promedio = (process_manager.suma_confianza / total) if total > 0 else 0
    madurez_promedio = (process_manager.suma_madurez / process_manager.conteo_madurez) if process_manager.conteo_madurez > 0 else 0
    
    resumen_data = {
        "lote_id": lote_id,
        "total_paltas": total,
        "cant_buenas": buenas,
        "cant_defectuosas": malas,
        "porcentaje_buenas": (buenas / total * 100) if total > 0 else 0,
        "porcentaje_defectuosas": (malas / total * 100) if total > 0 else 0,
        "madurez_promedio": madurez_promedio,
        "niveles_madurez": process_manager.conteo_niveles,
        "confianza_avg": conf_promedio,
        "finalizado_en": datetime.now().isoformat()
    }
    
    try:
        supabase.table("deteccion_resumen").insert(resumen_data).execute()
        supabase.table("lotes").update({"estado": EstadoLote.FINALIZADO.value}).eq("id", lote_id).execute()
        
        # Generar predicción ML automática para el lote
        from app.api.v1.endpoints.predicciones import generar_prediccion_lote
        from app.api.v1.endpoints.recomendaciones import generar_recomendacion_lote
        from uuid import UUID
        try:
            await generar_prediccion_lote(UUID(lote_id))
            print(f"[AUTO-PREDICCION] Predicción generada exitosamente para lote: {lote_id}")
            
            # Generar recomendación del Sistema Experto (pyDatalog)
            try:
                await generar_recomendacion_lote(UUID(lote_id))
                print(f"[AUTO-RECOMENDACION] Recomendación generada exitosamente para lote: {lote_id}")
            except Exception as rec_err:
                print(f"[ERROR AUTO-RECOMENDACION] Error al generar recomendación: {rec_err}")
                
        except Exception as pred_err:
            print(f"[ERROR AUTO-PREDICCION] Error al generar la predicción: {pred_err}")
            
    except Exception as e:
        print(f"[ERROR DB] No se guardó el resumen: {e}")
    
    process_manager.lote_id_activo = None
    return {"mensaje": "Captura detenida y predicción generada correctamente.", "pid": pid}

@router.get("/monitor/{lote_id}")
async def monitor_lote(lote_id: str, ultimas_lineas: int = 10):
    activa = process_manager.esta_activa()
    resumen = {"total_paltas": 0, "cant_buenas": 0, "cant_defectuosas": 0}
    
    if process_manager.lote_id_activo == lote_id:
        resumen = {
            "total_paltas": process_manager.total_paltas,
            "cant_buenas": process_manager.cant_buenas,
            "cant_defectuosas": process_manager.cant_defectuosas
        }

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

@router.get("/config-camara")
async def obtener_config_camara():
    """
    Devuelve la URL de la cámara celular configurada en el archivo .env.
    """
    return {"ip_camera_url": settings.IP_CAMARA_CELULAR}

@router.get("/clima-actual")
async def obtener_clima_actual_planta(
    ciudad: str = None,
    lat: float = None,
    lon: float = None
):
    """
    Retorna la temperatura actual y promedio del clima para la planta.
    """
    return obtener_clima_futuro(lugar_origen=ciudad, lat=lat, lon=lon)

@router.get("/")
async def root_captura():
    return {"mensaje": "Módulo de captura activo"}