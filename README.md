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
🥑 *AllinPalt API - Inteligencia Agrícola*