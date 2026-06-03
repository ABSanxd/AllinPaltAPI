from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core.database import supabase
from app.services.prediccion import calcular_dias_cosecha, calcular_prediccion
from app.services.clima import obtener_clima_futuro


router = APIRouter()


@router.post("/{lote_id}", status_code=201)
async def generar_prediccion_lote(lote_id: UUID):
    """
    Genera una predicción ML para un lote y la guarda en Supabase.
    """

    lote_id_str = str(lote_id)

    # 1. Obtener datos generales del lote
    lote_response = (
        supabase.table("lotes")
        .select("id, temperatura_ambiente, fecha_cosecha, lugar_origen")
        .eq("id", lote_id_str)
        .execute()
    )

    if not lote_response.data:
        raise HTTPException(status_code=404, detail="Lote no encontrado.")

    lote = lote_response.data[0]

    # Obtener el clima futuro para la ubicación de la planta de procesamiento (por defecto Lima)
    clima_data = obtener_clima_futuro("Lima")
    temp_futura = clima_data["promedio"] if isinstance(clima_data, dict) else clima_data

    # 2. Obtener la madurez promedio calculada durante la captura
    resumen_response = (
        supabase.table("deteccion_resumen")
        .select("madurez_promedio, finalizado_en")
        .eq("lote_id", lote_id_str)
        .order("finalizado_en", desc=True)
        .limit(1)
        .execute()
    )

    if not resumen_response.data:
        raise HTTPException(
            status_code=400,
            detail="El lote todavía no tiene resumen de detección."
        )

    resumen = resumen_response.data[0]

    temperatura = lote.get("temperatura_ambiente")
    madurez = resumen.get("madurez_promedio")
    fecha_cosecha = lote.get("fecha_cosecha")

    if temperatura is None:
        raise HTTPException(
            status_code=400,
            detail="El lote no tiene temperatura ambiente registrada."
        )

    if madurez is None:
        raise HTTPException(
            status_code=400,
            detail="El lote no tiene madurez promedio registrada."
        )

    # 3. Calcular días desde cosecha
    dias_cosecha = calcular_dias_cosecha(
        date.fromisoformat(fecha_cosecha) if fecha_cosecha else None
    )

    # Regla Directa para lotes 100% defectuosos (madurez promedio = 0)
    if float(madurez) < 1.0:
        prediccion_data = {
            "lote_id": lote_id_str,
            "vida_util_estimada": 0,
            "riesgo_deterioro": "ALTO",
            "prioridad_venta": "DESCARTE",
            "recomendacion": "Lote con 100% de descarte. No apto para exportación ni almacenamiento. Descartar de inmediato o derivar a procesamiento secundario.",
            "temperatura_ambiente": float(temperatura),
            "madurez_promedio": 0.0,
            "dias_cosecha": dias_cosecha,
            "temperatura_climatica_futura": temp_futura,
        }

        insert_response = (
            supabase.table("predicciones")
            .insert(prediccion_data)
            .execute()
        )

        if not insert_response.data:
            raise HTTPException(
                status_code=500,
                detail="No se pudo guardar la predicción para el lote defectuoso."
            )

        return {
            "mensaje": "Lote con 100% de descarte. Predicción directa guardada.",
            "algoritmo": "Regla de Negocio (Bypass)",
            "prediccion": insert_response.data[0],
        }

    # 4. Ejecutar predicción con Random Forest
    try:
        resultado = calcular_prediccion(
            temperatura=float(temperatura),
            madurez=float(madurez),
            dias_cosecha=dias_cosecha,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    # 5. Guardar resultado en Supabase
    prediccion_data = {
        "lote_id": lote_id_str,
        "vida_util_estimada": resultado["vida_util_estimada"],
        "riesgo_deterioro": resultado["riesgo_deterioro"],
        "prioridad_venta": resultado["prioridad_venta"],
        "temperatura_ambiente": float(temperatura),
        "madurez_promedio": float(madurez),
        "dias_cosecha": dias_cosecha,
        "temperatura_climatica_futura": temp_futura,
    }

    insert_response = (
        supabase.table("predicciones")
        .insert(prediccion_data)
        .execute()
    )

    if not insert_response.data:
        raise HTTPException(
            status_code=500,
            detail="No se pudo guardar la predicción."
        )

    return {
        "mensaje": "Predicción ML generada y guardada correctamente.",
        "algoritmo": resultado["algoritmo"],
        "prediccion": insert_response.data[0],
    }


@router.get("/{lote_id}")
async def consultar_predicciones_lote(lote_id: UUID):
    """
    Consulta la predicción más reciente guardada de un lote.
    """

    lote_id_str = str(lote_id)

    response = (
        supabase.table("predicciones")
        .select("*")
        .eq("lote_id", lote_id_str)
        .order("creado_at", desc=True)
        .limit(1)
        .execute()
    )

    if not response.data:
        return {}
    
    prediccion = response.data[0]

    # Consultar el resumen de detección para calcular el % de defectuosas
    resumen_resp = (
        supabase.table("deteccion_resumen")
        .select("total_paltas, cant_defectuosas")
        .eq("lote_id", lote_id_str)
        .order("finalizado_en", desc=True)
        .limit(1)
        .execute()
    )

    pct_defectuosas = 0.0
    if resumen_resp.data:
        resumen = resumen_resp.data[0]
        total = resumen.get("total_paltas", 0)
        defectuosas = resumen.get("cant_defectuosas", 0)
        if total > 0:
            pct_defectuosas = (defectuosas / total) * 100

    prediccion["porcentaje_defectuosas"] = pct_defectuosas
    return prediccion