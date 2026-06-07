from pathlib import Path
import csv


OUTPUT_PATH = Path("data/predicciones_entrenamiento.csv")

TEMPERATURAS = [4, 5, 7, 10, 13, 15, 20, 25, 28]
MADURECES = [1, 2, 3, 4, 5]
DIAS_COSECHA = [0, 3, 7, 10, 14, 21]


def vida_base_por_madurez(madurez: int) -> int:
    """
    Vida útil base bajo condiciones de almacenamiento controlado.
    La escala de madurez es visual-operativa, no materia seca directa.
    """
    return {
        1: 24,  # inmadura visualmente: no prioridad de venta, pero vida útil alta
        2: 28,  # cercana a madurez fisiológica / buena para almacenamiento
        3: 24,  # madurez comercial adecuada
        4: 10,  # madura: venta rápida
        5: 4,   # sobremadura: deterioro probable
    }[madurez]


def factor_temperatura(temp: float) -> float:
    """
    Factor basado en criterios técnicos de postcosecha.
    UC Davis recomienda 5–13 °C para palta mature-green y muestra
    aumento de respiración a 20 °C.
    """
    if temp < 4:
        return 0.45  # riesgo por frío excesivo
    if 4 <= temp <= 7:
        return 1.00  # rango óptimo/conservador
    if 7 < temp <= 13:
        return 0.75  # aceptable
    if 13 < temp < 20:
        return 0.45  # maduración acelerada
    return 0.25      # >=20 °C, alto riesgo


def calcular_vida_util(temp: float, madurez: int, dias: int) -> int:
    vida = vida_base_por_madurez(madurez) * factor_temperatura(temp)
    vida = vida - dias
    return max(0, min(28, round(vida)))


def calcular_riesgo(temp: float, madurez: int, dias: int, vida: int) -> str:
    if (
        madurez >= 5
        or temp >= 20
        or temp < 4
        or dias >= 14
        or vida <= 5
    ):
        return "ALTO"

    if (
        madurez >= 4
        or temp > 13
        or dias >= 7
        or vida <= 12
    ):
        return "MEDIO"

    return "BAJO"


def calcular_prioridad(madurez: int, vida: int, riesgo: str) -> str:
    if riesgo == "ALTO" or vida <= 7 or madurez >= 4:
        return "ALTA"

    if riesgo == "MEDIO" or vida <= 20 or madurez == 3:
        return "MEDIA"

    return "BAJA"


def generar_dataset() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    filas = []

    for temp in TEMPERATURAS:
        for madurez in MADURECES:
            for dias in DIAS_COSECHA:
                vida = calcular_vida_util(temp, madurez, dias)
                riesgo = calcular_riesgo(temp, madurez, dias, vida)
                prioridad = calcular_prioridad(madurez, vida, riesgo)

                filas.append({
                    "temperatura_ambiente": temp,
                    "madurez_promedio": madurez,
                    "dias_cosecha": dias,
                    "vida_util_estimada": vida,
                    "riesgo_deterioro": riesgo,
                    "prioridad_venta": prioridad,
                })

    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as archivo:
        writer = csv.DictWriter(
            archivo,
            fieldnames=[
                "temperatura_ambiente",
                "madurez_promedio",
                "dias_cosecha",
                "vida_util_estimada",
                "riesgo_deterioro",
                "prioridad_venta",
            ],
        )
        writer.writeheader()
        writer.writerows(filas)

    print(f"CSV generado correctamente en: {OUTPUT_PATH}")
    print(f"Total de filas: {len(filas)}")


if __name__ == "__main__":
    generar_dataset()