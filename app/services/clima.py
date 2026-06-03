import requests
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

OPENWEATHER_API_KEY = settings.OPENWEATHER_API_KEY
OPENWEATHER_FORECAST_URL = "http://api.openweathermap.org/data/2.5/forecast"
OPENWEATHER_CURRENT_URL = "http://api.openweathermap.org/data/2.5/weather"
TEMPERATURA_FALLBACK = 20.0


def obtener_clima_futuro(lugar_origen: str = None, lat: float = None, lon: float = None) -> dict:
    """
    Obtiene la temperatura actual en tiempo real y el promedio de temperatura climática futura para los próximos 5 días
    desde la API de OpenWeatherMap.

    Returns:
        Diccionario con {"actual": float, "promedio": float}
    """
    fallback = {"actual": TEMPERATURA_FALLBACK, "promedio": TEMPERATURA_FALLBACK}

    params = {
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",  # Celsius
        "lang": "es",
    }

    if lat is not None and lon is not None:
        params["lat"] = lat
        params["lon"] = lon
        loc_str = f"Coordenadas ({lat}, {lon})"
    elif lugar_origen and lugar_origen.strip():
        params["q"] = lugar_origen.strip()
        loc_str = lugar_origen.strip()
    else:
        logger.warning("No se proporcionó ciudad ni coordenadas, usando temperatura fallback.")
        return fallback

    actual_temp = TEMPERATURA_FALLBACK
    promedio = TEMPERATURA_FALLBACK

    # 1. Obtener clima actual en tiempo real
    try:
        response_curr = requests.get(OPENWEATHER_CURRENT_URL, params=params, timeout=5)
        if response_curr.status_code == 200:
            data_curr = response_curr.json()
            if "main" in data_curr and "temp" in data_curr["main"]:
                actual_temp = data_curr["main"]["temp"]
        elif response_curr.status_code == 401:
            logger.error("API key de OpenWeatherMap inválida o no autorizada al consultar clima actual.")
            return fallback
    except Exception as e:
        logger.error("Error al consultar clima actual: %s", e)

    # 2. Obtener pronóstico de 5 días para calcular promedio futuro
    try:
        response_fore = requests.get(OPENWEATHER_FORECAST_URL, params=params, timeout=5)
        if response_fore.status_code == 200:
            data_fore = response_fore.json()
            temperaturas = [item["main"]["temp"] for item in data_fore.get("list", [])]
            if temperaturas:
                promedio = sum(temperaturas) / len(temperaturas)
            else:
                promedio = actual_temp
        elif response_fore.status_code == 401:
            logger.error("API key de OpenWeatherMap inválida o no autorizada al consultar pronóstico.")
            return fallback
    except Exception as e:
        logger.error("Error al consultar pronóstico: %s", e)
        promedio = actual_temp

    logger.info(
        "Clima para '%s': Actual %.2f°C | Promedio Futuro %.2f°C.",
        loc_str,
        actual_temp,
        promedio,
    )
    return {"actual": round(actual_temp, 2), "promedio": round(promedio, 2)}