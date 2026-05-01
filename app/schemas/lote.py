from pydantic import BaseModel
from typing import Optional

class LoteCreate(BaseModel):
    codigo_lote: str
    proveedor: str
    lugar_origen: str
    fecha_cosecha: Optional[str] = None
    temperatura_ambiente: Optional[float] = None
