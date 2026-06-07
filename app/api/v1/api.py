from fastapi import APIRouter
from app.api.v1.endpoints import lotes, captura, predicciones, recomendaciones

api_router = APIRouter()

api_router.include_router(lotes.router, prefix="/lotes", tags=["Lotes"])
api_router.include_router(captura.router, prefix="/captura", tags=["Captura"])
api_router.include_router(
    predicciones.router,
    prefix="/predicciones",
    tags=["Predicciones"],
)
api_router.include_router(
    recomendaciones.router,
    prefix="/recomendaciones",
    tags=["Recomendaciones"],
)