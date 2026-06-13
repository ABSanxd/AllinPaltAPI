from typing import Any
from pyDatalog import pyDatalog


# Términos lógicos de pyDatalog.
# Deben declararse a nivel de módulo.
pyDatalog.create_terms(
    "datos_lote, prioridad_descarte, prioridad_alta, prioridad_media, prioridad_baja, "
    "L, D, M, TA, TF"
)


# ============================================================
# REGLAS FORMALES DEL SISTEMA EXPERTO
# L  = lote_id lógico
# D  = días desde cosecha
# M  = madurez promedio YOLO
# TA = temperatura ambiente en planta
# TF = temperatura futura promedio por OpenWeather
# ============================================================

# Descarte: madurez 0 o casi 0 significa lote no apto.
prioridad_descarte(L) <= datos_lote(L, D, M, TA, TF) & (M < 1.0)

# Prioridad alta: vender/procesar rápido.
prioridad_alta(L) <= datos_lote(L, D, M, TA, TF) & (M >= 4.0)
prioridad_alta(L) <= datos_lote(L, D, M, TA, TF) & (D >= 7)
prioridad_alta(L) <= datos_lote(L, D, M, TA, TF) & (TA >= 25.0)
prioridad_alta(L) <= datos_lote(L, D, M, TA, TF) & (TF >= 25.0)
prioridad_alta(L) <= datos_lote(L, D, M, TA, TF) & (M >= 3.0) & (D >= 5)
prioridad_alta(L) <= datos_lote(L, D, M, TA, TF) & (M >= 3.0) & (TF >= 22.0)

# Prioridad media: lote vendible, pero requiere seguimiento.
prioridad_media(L) <= datos_lote(L, D, M, TA, TF) & (M >= 2.5)
prioridad_media(L) <= datos_lote(L, D, M, TA, TF) & (D >= 3)
prioridad_media(L) <= datos_lote(L, D, M, TA, TF) & (TA >= 20.0)
prioridad_media(L) <= datos_lote(L, D, M, TA, TF) & (TF >= 20.0)

# Prioridad baja: lote estable, poco maduro y con baja presión térmica.
prioridad_baja(L) <= datos_lote(L, D, M, TA, TF) & (M < 2.5) & (D < 3) & (TA < 20.0) & (TF < 20.0)


def _hay_respuesta(consulta: str) -> bool:
    respuesta = pyDatalog.ask(consulta)
    return respuesta is not None and respuesta.answers is not None


def _generar_factores(
    dias_cosecha: int,
    madurez_promedio: float,
    temperatura_ambiente: float,
    temperatura_futura: float,
) -> list[str]:
    factores = []

    if madurez_promedio < 1.0:
        factores.append("Madurez promedio menor a 1.0: lote considerado no apto.")

    if madurez_promedio >= 4.0:
        factores.append("Madurez promedio alta detectada por YOLO.")
    elif madurez_promedio >= 3.0:
        factores.append("Madurez promedio comercial/intermedia detectada por YOLO.")
    elif madurez_promedio >= 2.5:
        factores.append("Madurez cercana al punto comercial según escala visual-operativa.")

    if dias_cosecha >= 7:
        factores.append("Han pasado 7 o más días desde la cosecha.")
    elif dias_cosecha >= 3:
        factores.append("Han pasado 3 o más días desde la cosecha; requiere seguimiento.")

    if temperatura_ambiente >= 25.0:
        factores.append("Temperatura ambiente en planta igual o mayor a 25 °C.")
    elif temperatura_ambiente >= 20.0:
        factores.append("Temperatura ambiente en planta igual o mayor a 20 °C.")

    if temperatura_futura >= 25.0:
        factores.append("Temperatura futura promedio igual o mayor a 25 °C.")
    elif temperatura_futura >= 20.0:
        factores.append("Temperatura futura promedio igual o mayor a 20 °C.")

    if madurez_promedio >= 3.0 and dias_cosecha >= 5:
        factores.append("Madurez media/alta combinada con varios días desde cosecha.")

    if madurez_promedio >= 3.0 and temperatura_futura >= 22.0:
        factores.append("Madurez media/alta combinada con clima futuro cálido.")

    if not factores:
        factores.append("Condiciones generales estables según las reglas configuradas.")

    return factores


def evaluar_recomendacion(
    lote_id: str,
    dias_cosecha: int,
    madurez_promedio: float,
    temperatura_ambiente: float,
    temperatura_futura: float,
) -> dict[str, Any]:
    """
    Evalúa un lote usando reglas lógicas con pyDatalog.
    Devuelve prioridad de venta y recomendación final.
    """

    if madurez_promedio is None:
        raise ValueError("La madurez promedio es obligatoria.")

    if temperatura_ambiente is None:
        raise ValueError("La temperatura ambiente es obligatoria.")

    if temperatura_futura is None:
        raise ValueError("La temperatura futura es obligatoria.")

    dias_cosecha = int(dias_cosecha)
    madurez_promedio = float(madurez_promedio)
    temperatura_ambiente = float(temperatura_ambiente)
    temperatura_futura = float(temperatura_futura)

    if dias_cosecha < 0:
        raise ValueError("Los días desde cosecha no pueden ser negativos.")

    # Usamos una llave segura para pyDatalog.
    lote_logico = f"lote_{str(lote_id).replace('-', '_')}"

    pyDatalog.assert_fact(
        "datos_lote",
        lote_logico,
        dias_cosecha,
        madurez_promedio,
        temperatura_ambiente,
        temperatura_futura,
    )

    try:
        if _hay_respuesta(f"prioridad_descarte('{lote_logico}')"):
            prioridad = "DESCARTE"
            recomendacion = (
                "Lote no apto para venta directa. Derivar a descarte o procesamiento secundario "
                "según evaluación sanitaria interna."
            )
            regla = "prioridad_descarte"

        elif _hay_respuesta(f"prioridad_alta('{lote_logico}')"):
            prioridad = "ALTA"
            recomendacion = (
                "Priorizar venta inmediata o despacho rápido. Evitar almacenamiento prolongado "
                "porque existe alto riesgo de pérdida de vida útil."
            )
            regla = "prioridad_alta"

        elif _hay_respuesta(f"prioridad_media('{lote_logico}')"):
            prioridad = "MEDIA"
            recomendacion = (
                "Mantener en observación y programar venta en corto plazo. Requiere control de "
                "temperatura y seguimiento de madurez."
            )
            regla = "prioridad_media"

        else:
            prioridad = "BAJA"
            recomendacion = (
                "Lote estable. Puede almacenarse temporalmente bajo condiciones controladas, "
                "manteniendo monitoreo de temperatura y madurez."
            )
            regla = "prioridad_baja"

        return {
            "prioridad_venta": prioridad,
            "recomendacion": recomendacion,
            "regla_disparada": regla,
            "factores": _generar_factores(
                dias_cosecha=dias_cosecha,
                madurez_promedio=madurez_promedio,
                temperatura_ambiente=temperatura_ambiente,
                temperatura_futura=temperatura_futura,
            ),
            "entradas": {
                "dias_cosecha": dias_cosecha,
                "madurez_promedio": madurez_promedio,
                "temperatura_ambiente": temperatura_ambiente,
                "temperatura_futura": temperatura_futura,
            },
            "motor": "pyDatalog",
        }

    finally:
        # Limpieza del hecho temporal para no contaminar otras evaluaciones.
        pyDatalog.retract_fact(
            "datos_lote",
            lote_logico,
            dias_cosecha,
            madurez_promedio,
            temperatura_ambiente,
            temperatura_futura,
        )