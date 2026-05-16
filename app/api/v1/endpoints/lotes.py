from fastapi import APIRouter, HTTPException
from app.schemas.lote import LoteCreate
from app.core.database import supabase
from app.core.nomenclatura import generar_codigo_lote

router = APIRouter()

@router.post("/", status_code=201)
async def crear_lote(lote: LoteCreate):
    # Generar el código de lote automáticamente en el backend
    codigo_autogenerado = generar_codigo_lote()
    
    data = {
        "codigo_lote": codigo_autogenerado,
        "proveedor": lote.proveedor,
        "lugar_origen": lote.lugar_origen,
        "fecha_cosecha": lote.fecha_cosecha.isoformat() if lote.fecha_cosecha else None,
        "temperatura_ambiente": lote.temperatura_ambiente,
        "estado": lote.estado.value
    }
    response = supabase.table("lotes").insert(data).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Error al crear el lote en Supabase")
    return {"mensaje": "Lote creado exitosamente", "data": response.data[0]}

@router.get("/")
async def listar_lotes():
    """
    Lista todos los lotes incluyendo su resumen de detecciones (Join).
    Esto es usado por el Historial para mostrar Totales, Buenas y Malas.
    """
    response = supabase.table("lotes")\
        .select("*, deteccion_resumen(*)")\
        .order("id", desc=True)\
        .execute()
    return {"lotes": response.data}

@router.get("/{lote_id}/resumen")
async def obtener_resumen_lote(lote_id: str):
    """
    Devuelve el resumen acumulado en memoria para el Dashboard.
    Evita consultas pesadas a la base de datos por cada palta.
    """
    from app.core.process import process_manager
    
    # Solo devolvemos datos si el lote solicitado es el que está activo
    if process_manager.lote_id_activo == lote_id:
        return {
            "total_paltas": process_manager.total_paltas,
            "cant_buenas": process_manager.cant_buenas,
            "cant_defectuosas": process_manager.cant_defectuosas
        }
    
    # Si no es el lote activo, podríamos buscar el resumen final en la BD
    res_final = supabase.table("deteccion_resumen").select("*").eq("lote_id", lote_id).execute()
    if res_final.data:
        res = res_final.data[0]
        return {
            "total_paltas": res["total_paltas"],
            "cant_buenas": res["cant_buenas"],
            "cant_defectuosas": res["cant_defectuosas"]
        }

    return {
        "total_paltas": 0,
        "cant_buenas": 0,
        "cant_defectuosas": 0
    }
