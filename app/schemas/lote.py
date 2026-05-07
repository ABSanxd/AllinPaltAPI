from datetime import date
from typing import Optional
from pydantic import BaseModel, Field
from app.schemas.enums import EstadoLote


class LoteCreate(BaseModel):
    codigo_lote: str = Field(..., min_length=3, max_length=50)
    proveedor: str = Field(..., min_length=2, max_length=120)
    lugar_origen: str = Field(..., min_length=2, max_length=120)
    fecha_cosecha: Optional[date] = None
    temperatura_ambiente: Optional[float] = Field(default=None, ge=-10, le=60)
    estado: EstadoLote = EstadoLote.REGISTRADO