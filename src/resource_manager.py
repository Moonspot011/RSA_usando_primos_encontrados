import psutil

class ResourceManager:
    """Monitorea el consumo y la disponibilidad de recursos locales."""
    
    @staticmethod
    def get_local_resources():
        # CPU disponible en porcentaje (100 - consumo actual)
        cpu_free = 100.0 - psutil.cpu_percent(interval=None)
        
        # Memoria RAM libre en MB
        ram_memory = psutil.virtual_memory()
        ram_free_mb = ram_memory.available / (1024 * 1024)
        
        return {
            "cpu_free_pct": round(cpu_free, 2),
            "ram_free_mb": round(ram_free_mb, 2)
        }