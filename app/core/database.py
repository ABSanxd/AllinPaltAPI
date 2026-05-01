from supabase import create_client, Client
from app.core.config import settings

if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("Faltan las credenciales de Supabase en el archivo .env")

# Cliente único para toda la aplicación
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
