from datetime import datetime
from app.core.database import supabase

def generar_codigo_lote() -> str:
    """
    Genera automáticamente un código de lote correlativo con el formato LOT-000X-YY.
    Ejemplo: si hay 3 lotes en 2026, generará LOT-0004-26.
    """
    try:
        # Hacemos una consulta rápida contando los registros existentes
        response = supabase.table("lotes").select("id", count="exact").execute()
        if hasattr(response, "count") and response.count is not None:
            conteo_actual = response.count
        else:
            conteo_actual = len(response.data) if response.data else 0
    except Exception:
        # En caso de cualquier falla de conexión o base de datos, usamos un fallback a 0
        conteo_actual = 0

    siguiente_numero = conteo_actual + 1
    
    # Obtener los últimos 2 dígitos del año actual
    anio_2_digitos = datetime.now().strftime("%y") # "26" para 2026, "24" para 2024, etc.
    
    # Formatear a LOT-000X-YY (4 dígitos para el correlativo, 2 para el año)
    return f"LOT-{siguiente_numero:04d}-{anio_2_digitos}"
