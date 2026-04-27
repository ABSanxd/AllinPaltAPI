import os
import logging
from contextlib import asynccontextmanager

# Suprimir logs verbosos de TensorFlow ANTES de importar keras/tf
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")   # silencia C++ logs
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")  # desactiva oneDNN warnings
logging.getLogger("tensorflow").setLevel(logging.ERROR)
logging.getLogger("absl").setLevel(logging.ERROR)

from fastapi import FastAPI, UploadFile, File, HTTPException
from app.use_cases.analizar_imagen import AnalizarImagen

# Contenedor del caso de uso (se llena en el lifespan)
_state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Carga el modelo una sola vez al iniciar el servidor."""
    print("🥑  Cargando modelo de clasificación de paltas...")
    _state["analizar_imagen"] = AnalizarImagen()
    print("✅  Modelo cargado. Servidor listo.")
    yield
    # Limpieza al apagar (opcional)
    _state.clear()


app = FastAPI(
    title="AllinPalt API",
    description="API para análisis de paltas usando visión por computadora.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {"message": "AllinPalt API activa 🥑"}


@app.post("/analizar-imagen")
async def analizar_imagen(imagen: UploadFile = File(...)):
    """
    Recibe una imagen de palta y determina su estado.

    - **True**  → Buen Estado
    - **False** → Defectuosa
    """
    if not imagen.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="El archivo enviado no es una imagen válida.",
        )

    imagen_bytes = await imagen.read()

    try:
        caso_uso: AnalizarImagen = _state["analizar_imagen"]
        resultado: bool = caso_uso.execute(imagen_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar la imagen: {str(e)}",
        )

    return {
        "buen_estado": resultado,
        "estado": "Buen Estado" if resultado else "Defectuosa",
    }
