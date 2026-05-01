from enum import Enum

class EstadoLote(str, Enum):
    REGISTRADO = "registrado"
    EN_PROCESO = "en_proceso"
    FINALIZADO = "finalizado"

class RiesgoDeterioro(str, Enum):
    BAJO = "bajo"
    MEDIO = "medio"
    ALTO = "alto"

class PrioridadVenta(str, Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"