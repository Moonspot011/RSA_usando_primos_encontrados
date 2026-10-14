import os
import time
import logging
from src.messaging import MessageService
from src.discovery import DiscoveryService
from src.scheduler import DistributedScheduler
from src.task_manager import TaskManager
from src.inference.ai_worker import AIWorker
from src.crypto.cryptosystems import crear_cripto
from src.crypto.lote import fuente_para_nodo

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)

class ComplexNode:
    def __init__(self, node_id, host, port, known_ports, algo=None):
        self.node_id = node_id
        self.port = port

        # Par de llaves del nodo (primos aleatorios de 40 dígitos). Algoritmo: 'rsa' o 'elgamal'
        algo = algo or os.environ.get("CRYPTO_ALGO", "rsa")
        # p y q se toman del lote de primos hallados (primos.txt), eligiéndolos con la fecha
        fuente, detalle = fuente_para_nodo(node_id)
        if fuente is None:
            logging.warning(f"[CRYPTO] Sin lote de primos ({detalle}); se generan primos nuevos")
        self.crypto = crear_cripto(algo, fuente=fuente)
        origen = f"del {detalle}" if fuente is not None else "generados al vuelo"
        logging.info(f"[CRYPTO] Nodo {node_id}: llaves {self.crypto.algo.upper()} con primos {origen}")

        self.ai_worker = AIWorker(model_name=f"model_{node_id}")
        self.messaging = MessageService(host, port, self.handle_message, self.crypto)
        self.discovery = DiscoveryService(node_id, port, known_ports, self.messaging,
                                          public_key=self.crypto.public_key())
        self.scheduler = DistributedScheduler()
        self.task_manager = TaskManager(node_id, self.scheduler, self.messaging, self.discovery)

    def start(self):
        logging.info(f"=== Iniciando Nodo {self.node_id} en puerto {self.port} ===")
        self.messaging.start()
        self.discovery.start()

    def handle_message(self, message, addr):
        msg_type = message["header"]["type"]
        sender_id = message["header"]["sender_id"]
        secure = message["header"].get("secure", False)

        if msg_type == "RESOURCE_BEACON":
            self.discovery.process_beacon(sender_id, addr[0], message["payload"])
        
        elif msg_type == "PUBKEY_REQUEST":
            # Handshake para clientes externos que aún no conocen nuestra clave pública
            response = {
                "header": {
                    "sender_id": self.node_id,
                    "type": "PUBKEY_RESPONSE",
                    "timestamp": time.time()
                },
                "payload": {"public_key": self.crypto.public_key()}
            }
            self.messaging.send_json(addr[0], addr[1], response)

        elif msg_type in ("TASK_SUBMIT", "TASK_RESULT") and not secure:
            logging.warning(f"[CRYPTO] {msg_type} de {sender_id} RECHAZADO: llegó sin cifrar")

        elif msg_type == "TASK_SUBMIT":
            payload = message["payload"]
            task_id = payload["task_id"]
            task_name = payload["task_name"]
            parameters = payload.get("parameters", {})

            logging.info(f"[EXECUTION] Recibida tarea de IA '{task_name}' ({task_id}) enviada por {sender_id}")
            
            # Ejecución en la capa de IA
            ai_response = self.ai_worker.run_inference(task_name, parameters)

            result_msg = {
                "header": {
                    "sender_id": self.node_id,
                    "type": "TASK_RESULT",
                    "timestamp": time.time()
                },
                "payload": {
                    "task_id": task_id,
                    "status": ai_response["status"],
                    "execution_time_sec": ai_response["execution_time_sec"],
                    "result_data": ai_response["result_data"]
                }
            }
            # Se responde cifrado con la clave pública de quien envió la tarea
            peer = self.discovery.peer_table.get(sender_id)
            reply_key = payload.get("reply_public_key")  # clientes externos (no son nodos)
            if peer and peer.public_key:
                self.messaging.send_secure(peer.ip, peer.port, result_msg, peer.public_key)
            elif reply_key:
                self.messaging.send_secure(addr[0], addr[1], result_msg, reply_key)
            else:
                logging.warning(f"[CRYPTO] No hay clave pública de {sender_id}; no se puede responder cifrado")

        elif msg_type == "TASK_RESULT":
            task_id = message["payload"]["task_id"]
            result = message["payload"]["result_data"]
            logging.info(f"[RESULT] Tarea {task_id} finalizada exitosamente por {sender_id}. Resultado: {result}")
            if task_id in self.task_manager.tasks:
                self.task_manager.tasks[task_id].status = "COMPLETED"

    def stop(self):
        logging.info(f"Deteniendo nodo {self.node_id}...")
        self.discovery.stop()
        self.messaging.stop()