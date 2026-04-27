# Crea entorno virtual: 
python -m venv .venv


# Activa:
.venv\Scripts\activate


# Instalar dependencias:
pip install -r requirements.txt


# Ejecutar api:
fastapi dev app/main.py


# Abre en navegador:
http://127.0.0.1:8000/docs