from fastapi import APIRouter, HTTPException
from app.schemas.lote import LoteCreate
from app.core.database import supabase

router = APIRouter()

@router.post("/", status_code=201)
async def crear_lote(lote: LoteCreate):
    data = {
        "codigo_lote": lote.codigo_lote,
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
    response = supabase.table("lotes").select("*").order("created_at", desc=True).execute()
    return {"lotes": response.data}
