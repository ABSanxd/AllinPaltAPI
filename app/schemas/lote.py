from datetime import date, timedelta
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from app.schemas.enums import EstadoLote


class LoteCreate(BaseModel):
    codigo_lote: Optional[str] = Field(default=None, max_length=50)
    proveedor: str = Field(..., min_length=2, max_length=120)
    lugar_origen: str = Field(..., min_length=2, max_length=120)
    fecha_cosecha: Optional[date] = None
    temperatura_ambiente: Optional[float] = Field(default=None, ge=-10, le=60)
    estado: EstadoLote = EstadoLote.REGISTRADO
    
    @field_validator('fecha_cosecha')
    @classmethod
    def validar_fecha_cosecha(cls, v):
        if v is None:
            return v
        hoy = date.today()
        if v > hoy:
            raise ValueError('La fecha de cosecha no puede ser una fecha futura.')
        if v < hoy - timedelta(days=90):
            raise ValueError('La fecha de cosecha no puede ser mayor a 90 días atrás.')
        return v

    @field_validator('proveedor', 'lugar_origen')
    @classmethod
    def validar_no_solo_espacios(cls, v):
        if not v.strip():
            raise ValueError('El campo no puede contener solo espacios en blanco.')
        return v.strip()