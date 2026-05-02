from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.v1.api import api_router
from app.use_cases.analizar_imagen import AnalizarImagen
from app.core.process import process_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Carga el modelo una sola vez al iniciar el servidor."""
    print("🥑  Cargando modelo de clasificación de paltas...")
    # Guardamos la instancia directamente en el estado de la app de FastAPI
    app.state.analizador = AnalizarImagen()
    print("✅  Modelo cargado. Servidor listo.")
    yield
    # Limpieza al apagar el servidor
    process_manager.detener_captura()

app = FastAPI(
    title="AllinPalt API",
    description="Sistema inteligente para trazabilidad y calidad de paltas.",
    version="2.1.0",
    lifespan=lifespan,
)

# ── Configuración de CORS ─────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todos los orígenes en desarrollo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Registro de Rutas ─────────────────────────────────────────────────────────
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "AllinPalt API activa 🥑"}