from datetime import date
from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core.database import supabase
from app.services.clima import obtener_clima_futuro
from app.services.prediccion import calcular_dias_cosecha
from app.services.recomendacion import evaluar_recomendacion


router = APIRouter()


@router.get("/{lote_id}")
async def generar_recomendacion_lote(lote_id: UUID):
    """
    Ejecuta el motor de reglas pyDatalog para un lote procesado.
    Guarda la prioridad de venta y la recomendación final junto a la predicción más reciente.
    """

    lote_id_str = str(lote_id)

    lote_response = (
        supabase.table("lotes")
        .select("id, temperatura_ambiente, fecha_cosecha, lugar_origen")
        .eq("id", lote_id_str)
        .execute()
    )

    if not lote_response.data:
        raise HTTPException(status_code=404, detail="Lote no encontrado.")

    lote = lote_response.data[0]

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
            detail="El lote todavía no tiene resumen de detección. Primero procesa el lote con YOLO.",
        )

    resumen = resumen_response.data[0]

    madurez_promedio = resumen.get("madurez_promedio")
    temperatura_ambiente = lote.get("temperatura_ambiente")
    fecha_cosecha = lote.get("fecha_cosecha")
    lugar_origen = lote.get("lugar_origen") or "Lima,PE"

    if madurez_promedio is None:
        raise HTTPException(
            status_code=400,
            detail="El lote no tiene madurez promedio registrada.",
        )

    clima_data = obtener_clima_futuro(lugar_origen)

    temperatura_actual_clima = clima_data.get("actual")
    temperatura_futura = clima_data.get("promedio")

    if temperatura_ambiente is None:
        temperatura_ambiente = temperatura_actual_clima

    if temperatura_ambiente is None:
        raise HTTPException(
            status_code=400,
            detail="No se pudo determinar temperatura ambiente para el lote.",
        )

    if temperatura_futura is None:
        raise HTTPException(
            status_code=400,
            detail="No se pudo determinar temperatura futura para el lote.",
        )

    dias_cosecha = calcular_dias_cosecha(
        date.fromisoformat(fecha_cosecha) if fecha_cosecha else None
    )

    try:
        resultado = evaluar_recomendacion(
            lote_id=lote_id_str,
            dias_cosecha=dias_cosecha,
            madurez_promedio=float(madurez_promedio),
            temperatura_ambiente=float(temperatura_ambiente),
            temperatura_futura=float(temperatura_futura),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    prediccion_response = (
        supabase.table("predicciones")
        .select("id, vida_util_estimada, riesgo_deterioro")
        .eq("lote_id", lote_id_str)
        .order("creado_at", desc=True)
        .limit(1)
        .execute()
    )

    if not prediccion_response.data:
        raise HTTPException(
            status_code=400,
            detail="Primero genera una predicción ML para este lote antes de guardar la recomendación.",
        )

    prediccion_id = prediccion_response.data[0]["id"]
    prediccion_actual = prediccion_response.data[0]
    vida_util_estimada = prediccion_actual.get("vida_util_estimada")
    riesgo_deterioro = prediccion_actual.get("riesgo_deterioro")
    
    prioridad_final = resultado["prioridad_venta"]
    recomendacion_final = resultado["recomendacion"]

    if riesgo_deterioro == "ALTO" or (vida_util_estimada is not None and int(vida_util_estimada) <= 5):
        prioridad_final = "ALTA"
        recomendacion_final = (
            "Priorizar venta inmediata o derivar a procesamiento rápido. "
            "La predicción indica alto riesgo de deterioro o vida útil muy corta."
        )

    update_data = {
        "prioridad_venta": prioridad_final,
        "recomendacion": recomendacion_final,
        "temperatura_ambiente": float(temperatura_ambiente),
        "temperatura_climatica_futura": float(temperatura_futura),
        "madurez_promedio": float(madurez_promedio),
        "dias_cosecha": dias_cosecha,
    }

    update_response = (
        supabase.table("predicciones")
        .update(update_data)
        .eq("id", prediccion_id)
        .execute()
    )

    if not update_response.data:
        raise HTTPException(
            status_code=500,
            detail="No se pudo guardar la recomendación en Supabase.",
        )

    return {
        "mensaje": "Recomendación generada y guardada correctamente.",
        "lote_id": lote_id_str,
        "resultado": resultado,
        "prediccion_actualizada": update_response.data[0],
        "ajuste_por_prediccion_ml": {
            "vida_util_estimada": vida_util_estimada,
            "riesgo_deterioro": riesgo_deterioro,
            "prioridad_final": prioridad_final,
        },
    }