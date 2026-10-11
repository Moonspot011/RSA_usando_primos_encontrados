import time
import logging

class AIWorker:
    """Capa encarga de ejecutar las inferencias o tareas de IA en el nodo local."""
    
    def __init__(self, model_name: str = "mini_model_v1"):
        self.model_name = model_name
        self.model = None
        self._load_model()

    def _load_model(self):
        """Carga en memoria el modelo de IA deseado."""
        logging.info(f"[AI_WORKER] Cargando modelo local '{self.model_name}'...")
        # Aquí cargarías en el futuro: self.model = torch.load(...)
        self.model = "MOCK_AI_MODEL_LOADED"

    def run_inference(self, task_name: str, parameters: dict) -> dict:
        """Ejecuta la inferencia recibida."""
        start_time = time.time()
        logging.info(f"[AI_WORKER] Procesando inferencia '{task_name}'...")

        # Simulación de inferencia
        if task_name == "regresion_lineal":
            result_data = {"slope": 2.35, "intercept": 0.81, "mse": 0.04}
        else:
            result_data = {"prediction": "Clase_A", "confidence": 0.96}

        execution_time = round(time.time() - start_time, 4)
        
        return {
            "status": "COMPLETED",
            "execution_time_sec": execution_time,
            "result_data": result_data
        }