import requests
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

OPENWEATHER_API_KEY = settings.OPENWEATHER_API_KEY
OPENWEATHER_FORECAST_URL = "http://api.openweathermap.org/data/2.5/forecast"
TEMPERATURA_FALLBACK = 20.0


def obtener_clima_futuro(lugar_origen: str) -> float:
    """
    Obtiene el promedio de temperatura climática futura para los próximos 5 días
    desde la API gratuita de OpenWeatherMap (endpoint /forecast).

    Args:
        lugar_origen: Nombre de la ciudad o lugar de origen del lote
                      (ej: "Lima", "Ica", "Trujillo").

    Returns:
        Promedio de temperaturas pronosticadas en grados Celsius.
        Retorna 20.0 como fallback si la API falla o el lugar no es encontrado.
    """
    if not lugar_origen or not lugar_origen.strip():
        logger.warning("lugar_origen vacío, usando temperatura fallback.")
        return TEMPERATURA_FALLBACK

    params = {
        "q": lugar_origen.strip(),
        "appid": OPENWEATHER_API_KEY,
        "units": "metric",  # Celsius
        "lang": "es",
    }

    try:
        response = requests.get(OPENWEATHER_FORECAST_URL, params=params, timeout=5)

        if response.status_code == 200:
            data = response.json()
            temperaturas = [item["main"]["temp"] for item in data["list"]]

            if not temperaturas:
                logger.warning("La API no retornó registros de temperatura para '%s'.", lugar_origen)
                return TEMPERATURA_FALLBACK

            promedio = sum(temperaturas) / len(temperaturas)
            logger.info(
                "Temperatura futura promedio para '%s': %.2f°C (basada en %d registros).",
                lugar_origen,
                promedio,
                len(temperaturas),
            )
            return round(promedio, 2)

        elif response.status_code == 404:
            logger.warning("Lugar '%s' no encontrado en OpenWeatherMap.", lugar_origen)
        elif response.status_code == 401:
            logger.error("API key de OpenWeatherMap inválida o no autorizada.")
        else:
            logger.error(
                "Error inesperado de OpenWeatherMap. Status: %d, Respuesta: %s",
                response.status_code,
                response.text,
            )

    except requests.exceptions.Timeout:
        logger.error("Timeout al consultar OpenWeatherMap para '%s'.", lugar_origen)
    except requests.exceptions.ConnectionError:
        logger.error("Error de conexión al consultar OpenWeatherMap.")
    except (KeyError, ZeroDivisionError, ValueError) as e:
        logger.error("Error al procesar respuesta de OpenWeatherMap: %s", e)

    return TEMPERATURA_FALLBACK