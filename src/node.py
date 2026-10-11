import time
import logging
from src.messaging import MessageService
from src.discovery import DiscoveryService
from src.scheduler import DistributedScheduler
from src.task_manager import TaskManager
from src.inference.ai_worker import AIWorker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)

class ComplexNode:
    def __init__(self, node_id, host, port, known_ports):
        self.node_id = node_id
        self.port = port
        
        self.ai_worker = AIWorker(model_name=f"model_{node_id}")
        self.messaging = MessageService(host, port, self.handle_message)
        self.discovery = DiscoveryService(node_id, port, known_ports, self.messaging)
        self.scheduler = DistributedScheduler()
        self.task_manager = TaskManager(node_id, self.scheduler, self.messaging, self.discovery)

    def start(self):
        logging.info(f"=== Iniciando Nodo {self.node_id} en puerto {self.port} ===")
        self.messaging.start()
        self.discovery.start()

    def handle_message(self, message, addr):
        msg_type = message["header"]["type"]
        sender_id = message["header"]["sender_id"]

        if msg_type == "RESOURCE_BEACON":
            self.discovery.process_beacon(sender_id, addr[0], message["payload"])
        
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
            peer = self.discovery.peer_table.get(sender_id)
            if peer:
                self.messaging.send_json(peer.ip, peer.port, result_msg)

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