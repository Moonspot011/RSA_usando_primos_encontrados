import time

class NodeInfo:
    """Representa la información de un vecino en la red."""
    def __init__(self, node_id, ip, port, cpu_free, ram_free, public_key=None):
        self.node_id = node_id
        self.ip = ip
        self.port = port
        self.cpu_free = cpu_free
        self.ram_free = ram_free
        self.public_key = public_key  # clave pública (RSA/ElGamal) publicada en el beacon
        self.last_seen = time.time()
        self.status = "ONLINE"

    def to_dict(self):
        return {
            "node_id": self.node_id,
            "ip": self.ip,
            "port": self.port,
            "cpu_free": self.cpu_free,
            "ram_free": self.ram_free,
            "status": self.status
        }

class Task:
    """Representa una tarea de cómputo/IA a ejecutar."""
    def __init__(self, task_id, name, params, cpu_req=10.0, ram_req=100.0):
        self.task_id = task_id
        self.name = name
        self.params = params
        self.cpu_req = cpu_req
        self.ram_req = ram_req
        self.assigned_to = None
        self.status = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED
