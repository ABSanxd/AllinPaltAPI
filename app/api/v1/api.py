from fastapi import APIRouter
from app.api.v1.endpoints import lotes, captura

api_router = APIRouter()

api_router.include_router(lotes.router, prefix="/lotes", tags=["Lotes"])
api_router.include_router(captura.router, prefix="/captura", tags=["Captura"])