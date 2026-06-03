# 🥑 AllinPalt API - Sistema Inteligente

Sistema inteligente para la clasificación, trazabilidad y predicción de calidad en paltas.

## 🛠️ Configuración del Entorno

1. **Crear entorno virtual:**
   ```bash
   python -m venv .venv
   ```

2. **Activar entorno:**
   ```bash
   .venv\Scripts\activate
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ejecutar API:**
   ```bash
   fastapi dev app/main.py
   ```

5. **Documentación Interactiva:**
   Abre [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) en tu navegador.

---

# **🏛️ Arquitectura de Software: AllinPalt API**

### **Estructura de Directorios**

```text
app/
├── api/                 # Capa de Entrada (Controllers)
│   └── v1/              # Versión de la API
│       ├── api.py       # Punto de unión de todas las rutas
│       └── endpoints/   # Rutas separadas por entidad
│           ├── lotes.py      # GET/POST de lotes
│           └── captura.py    # Control de cámara y análisis
│
├── core/                # Capa de Configuración (Config/Utils)
│   ├── config.py        # Carga de variables .env
│   ├── database.py      # Cliente de Supabase
│   └── process.py       # Gestión del subproceso de la cámara
│
├── schemas/             # Capa de Definición de Datos (Pydantic)
│   ├── enums.py         # Estados (registrado, finalizado, etc.)
│   ├── lote.py          # Validaciones para crear/leer lotes
│   └── deteccion.py     # Validaciones para resultados de visión
│
├── use_cases/           # Capa de Lógica de Negocio (Services)
│   ├── lotes_service.py      # Acciones relacionadas con lotes
│   ├── analizar_paltas.py    # Orquestador de YOLO + Madurez
│   └── predecir_calidad.py   # Lógica de vida útil (Módulos D y E)
│
├── ml_models/           # Capa de Inteligencia (Archivos binarios)
│   ├── yolo_paltas.pt   # Modelo YOLOv8
│   └── maturity_v1.h5   # Modelo de madurez
│
├── scripts/             # Procesos Independientes
│   └── captura_camara.py
│
└── main.py              # Punto de Arranque (Inicializa la App)
```

---

### **📝 Responsabilidades de cada capa (Reglas de Oro)**

1. **`main.py` (El Conserje):** Su única función es crear la instancia de `FastAPI()`, registrar las rutas de la carpeta `api/v1` y configurar los permisos (CORS). **No debe tener lógica.**
2. **`api/endpoints/` (Los Recepcionistas):** Solo manejan peticiones HTTP. Reciben el JSON, lo validan con un *Schema* y llaman a un *Use Case*. **No saben cómo guardar en la base de datos.**
3. **`use_cases/` (Los Especialistas):** Aquí vive la "magia". Ellos reciben datos limpios, llaman a los modelos de IA, hacen cálculos y deciden qué se guarda en Supabase.
4. **`core/` (Las Herramientas):** Cosas que todos necesitan pero nadie quiere programar dos veces: conexión a la DB y el manejo de los procesos de la cámara.
5. **`schemas/` (Los Contratos):** Aseguran que los datos tengan el formato correcto. Si el frontend envía mal un dato, esta capa lo rebota antes de que toque la lógica.

---

### **🏷️ Convenciones de Nombres**

Para mantener el código limpio y consistente, seguimos estas reglas:

- **Carpetas y Archivos:** Siempre en minúsculas y con guiones bajos (`use_cases`, `crear_lote.py`).
- **Clases:** En PascalCase (`LoteCreate`, `AnalizarImagen`).
- **Funciones:** En snake_case (`obtener_lotes_activos`).

---
---

## ⚙️ Configuración Adicional y Nuevas Funcionalidades

### 1. Variables de Entorno (`.env`)
Asegúrate de copiar el archivo `app/.env.example` como `app/.env` y completar los siguientes valores clave:

* **`IP_CAMARA_CELULAR`**: Si utilizas la aplicación **IP Webcam** en tu celular, ingresa la URL de transmisión de video (usualmente `http://192.168.0.x:8080/video`). Si usas una webcam local o cámara integrada, puedes configurarlo en `0`.
* **`OPENWEATHER_API_KEY`**: Tu API Key de OpenWeatherMap. Es necesaria para recuperar el clima real de la planta y el pronóstico de 5 días.

### 2. Autocompletado Climático Inteligente
Durante el registro de un nuevo lote, el frontend utiliza la **geolocalización del navegador** para obtener las coordenadas de la planta de procesamiento y consultar la API:
* **Temperatura Ambiente (Actual)**: Recupera la temperatura en vivo usando el endpoint `/weather` (más cercana a la de Google).
* **Temperatura Climática Futura (5 días)**: Realiza el promedio matemático del pronóstico de 5 días de OpenWeatherMap (`/forecast`), cubriendo los bloques diurnos y nocturnos.

### 3. Filtro de Confianza Inteligente por Etiqueta (YOLO)
Para evitar falsos positivos y mejorar el conteo del lote:
* El modelo YOLO realiza una inferencia general con una confianza baja (`conf=0.45`).
* **Etiqueta `"defectuosa"`**: Se le aplica un filtro estricto de **mínimo 68% de confianza (`confianza >= 0.68`)**. Si es menor, no se reporta como defecto.
* **Etiquetas de madurez** (`"madurez_1"`, etc.): Se les aplica un filtro flexible de **mínimo 48% de confianza (`confianza >= 0.48`)** para asegurar un registro fluido de la madurez.

### 4. Tracking Espacial Inteligente por Clase
Para evitar contar una misma palta varias veces y permitir pruebas manuales en un mismo punto físico:
* El sistema rastrea las coordenadas $(x, y)$ de cada palta.
* Si se detecta una nueva palta en la misma coordenada (distancia < 40px), solo se considerará repetida si mantiene la **misma clase**. Si la clasificación cambia (ej. de `madurez_1` a `defectuosa` o a otra madurez), el sistema asume que es una palta nueva y la cuenta correctamente.

---
🥑 *AllinPalt API - Inteligencia Agrícola*