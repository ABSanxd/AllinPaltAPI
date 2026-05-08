from fastapi import APIRouter, HTTPException
from app.core.database import supabase

router = APIRouter()


@router.get("/")
async def obtener_historial():
    response = (
        supabase
        .table("lotes")
        .select(
            """
            id,
            codigo_lote,
            proveedor,
            lugar_origen,
            fecha_cosecha,
            temperatura_ambiente,
            estado,
            created_at,
            deteccion_resumen (
                total_detecciones,
                total_buenas,
                total_defectuosas,
                total_desconocidas,
                confianza_promedio
            )
            """
        )
        .order("created_at", desc=True)
        .execute()
    )

    if response.data is None:
        raise HTTPException(status_code=500, detail="Error al obtener historial")

    return {"historial": response.data}