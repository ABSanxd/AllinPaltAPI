import subprocess
from typing import Optional

class ProcessManager:
    """Gestiona el estado del subproceso de la cámara."""
    def __init__(self):
        self.proceso_captura: Optional[subprocess.Popen] = None
        self.log_file = None
        self.lote_id_activo: Optional[str] = None
        # Contadores en memoria para tiempo real
        self.total_paltas = 0
        self.cant_buenas = 0
        self.cant_defectuosas = 0
        self.suma_confianza = 0.0
        self.suma_madurez = 0.0
        self.conteo_madurez = 0
        # Guarda conteo por nivel: {"m1": 10, "m2": 5, ...}
        self.conteo_niveles = {}
        # Guarda posiciones detectadas en el frame anterior
        self.posiciones_frame_anterior = []
        #Guardará los bytes de la imagen con las cajas dibujadas
        self.ultimo_frame_dibujado = None

    def reset_contadores(self):
        self.total_paltas = 0
        self.cant_buenas = 0
        self.cant_defectuosas = 0
        self.suma_confianza = 0.0
        self.suma_madurez = 0.0
        self.conteo_madurez = 0
        self.conteo_niveles = {}
        self.posiciones_frame_anterior = []
        self.ultimo_frame_dibujado = None # Resetear al iniciar nuevo lote

    def esta_activa(self) -> bool:
        return self.proceso_captura is not None and self.proceso_captura.poll() is None

    def detener_captura(self) -> None:
        if self.esta_activa():
            self.proceso_captura.terminate()
            try:
                self.proceso_captura.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proceso_captura.kill()
        
        self.proceso_captura = None
        if self.log_file and not self.log_file.closed:
            self.log_file.close()
        self.log_file = None

# Instancia global para ser usada en los routers
process_manager = ProcessManager()
