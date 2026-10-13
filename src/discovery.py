import time
import threading
import logging
from src.models import NodeInfo
from src.resource_manager import ResourceManager

class DiscoveryService:
    """Maneja el descubrimiento automático y la detección de fallos."""
    
    def __init__(self, node_id, port, known_ports, messaging_service, public_key=None):
        self.node_id = node_id
        self.port = port
        self.known_ports = known_ports
        self.messaging = messaging_service
        self.public_key = public_key  # clave pública local, se publica en cada beacon
        self.peer_table = {}  # node_id -> NodeInfo
        self.running = False

    def start(self):
        self.running = True
        threading.Thread(target=self._beacon_loop, daemon=True).start()
        threading.Thread(target=self._failure_detector_loop, daemon=True).start()

    def _beacon_loop(self):
        """Envía RESOURCE_BEACON periódicamente cada 2 segundos."""
        while self.running:
            resources = ResourceManager.get_local_resources()
            beacon_msg = {
                "header": {
                    "sender_id": self.node_id,
                    "type": "RESOURCE_BEACON",
                    "timestamp": time.time()
                },
                "payload": {
                    "port": self.port,
                    "cpu_free_pct": resources["cpu_free_pct"],
                    "ram_free_mb": resources["ram_free_mb"],
                    "public_key": self.public_key
                }
            }
            for target_port in self.known_ports:
                if target_port != self.port:
                    self.messaging.send_json("127.0.0.1", target_port, beacon_msg)
            
            time.sleep(2)

    def process_beacon(self, sender_id, ip, payload):
        """Actualiza la tabla de vecinos al recibir un beacon."""
        port = payload["port"]
        cpu_free = payload["cpu_free_pct"]
        ram_free = payload["ram_free_mb"]
        public_key = payload.get("public_key")

        if sender_id not in self.peer_table:
            logging.info(f"[DISCOVERY] Nuevo nodo descubierto: {sender_id} en puerto {port}")
            self.peer_table[sender_id] = NodeInfo(sender_id, ip, port, cpu_free, ram_free, public_key)
        else:
            peer = self.peer_table[sender_id]
            peer.cpu_free = cpu_free
            peer.ram_free = ram_free
            peer.public_key = public_key  # se actualiza por si el nodo reinició con llaves nuevas
            peer.last_seen = time.time()
            
            if peer.status == "OFFLINE":
                peer.status = "ONLINE"
                logging.info(f"[RECOVERY] El nodo {sender_id} volvió a estar ONLINE")

    def _failure_detector_loop(self):
        """Detecta nodos caídos (>5 segundos sin beacons)."""
        while self.running:
            current_time = time.time()
            for node_id, peer in self.peer_table.items():
                if peer.status == "ONLINE" and (current_time - peer.last_seen) > 5.0:
                    peer.status = "OFFLINE"
                    logging.warning(f"[FAILURE] Nodo {node_id} inactivo (>5s sin respuestas). Estado: OFFLINE")
            time.sleep(1)

    def stop(self):
        self.running = False
