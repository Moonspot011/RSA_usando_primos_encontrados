import time
import logging

class TaskManager:
    """Supervisa el envío de tareas y gestiona la reasignación ante fallos."""
    
    def __init__(self, node_id, scheduler, messaging, discovery):
        self.node_id = node_id
        self.scheduler = scheduler
        self.messaging = messaging
        self.discovery = discovery
        self.tasks = {}  # task_id -> Task

    def submit_task(self, task):
        self.tasks[task.task_id] = task
        target_node = self.scheduler.select_best_node(self.discovery.peer_table, task)

        if not target_node:
            logging.warning(f"[TASK] No hay nodos aptos para la tarea {task.task_id}")
            return False

        if not target_node.public_key:
            logging.warning(f"[CRYPTO] {target_node.node_id} aún no publica su clave pública; "
                            f"no se envía la tarea {task.task_id}")
            return False

        task.assigned_to = target_node.node_id
        task.status = "RUNNING"
        
        logging.info(f"[SCHEDULER] Asignando tarea '{task.name}' ({task.task_id}) a nodo {target_node.node_id}")

        msg = {
            "header": {
                "sender_id": self.node_id,
                "type": "TASK_SUBMIT",
                "timestamp": time.time()
            },
            "payload": {
                "task_id": task.task_id,
                "task_name": task.name,
                "parameters": task.params
            }
        }
        self.messaging.send_secure(target_node.ip, target_node.port, msg, target_node.public_key)
        return True

    def check_and_reassign_failed_tasks(self):
        """Reasigna automáticamente tareas si el nodo ejecutor se apaga/cae."""
        for task in self.tasks.values():
            if task.status == "RUNNING" and task.assigned_to:
                assigned_peer = self.discovery.peer_table.get(task.assigned_to)
                if assigned_peer and assigned_peer.status == "OFFLINE":
                    logging.warning(f"[RECOVERY] Reasignando tarea {task.task_id} por caída de {task.assigned_to}")
                    task.status = "PENDING"
                    task.assigned_to = None
                    self.submit_task(task)
