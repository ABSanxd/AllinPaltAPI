import os
from dotenv import load_dotenv

# Buscar el .env en la raíz de /app
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(env_path)

class Settings:
    PROJECT_NAME: str = "AllinPalt API"
    PROJECT_VERSION: str = "2.1.0"
    
    SUPABASE_URL: str = os.getenv("SUPABASE_URL")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    # Ruta base para el log de captura
    _ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    LOG_CAPTURA_PATH: str = os.path.join(_ROOT, "captura_camara.log")

settings = Settings()
