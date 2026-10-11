import time
from src.messaging import MessageService
from src.models import Task

def send_test_task():
    # Nos conectamos como un cliente temporal en el puerto 9999
    messaging = MessageService("127.0.0.1", 9999, lambda msg, addr: None)
    messaging.start()
    time.sleep(1)

    # Creamos una tarea de prueba para la red
    task_payload = {
        "header": {
            "sender_id": "cliente-prueba",
            "type": "TASK_SUBMIT",
            "timestamp": time.time()
        },
        "payload": {
            "task_id": "task-101",
            "task_name": "regresion_lineal",
            "parameters": {"dataset": "ventas_2026", "learning_rate": 0.05}
        }
    }

    print("--> Enviando tarea de prueba a nodo-01 (puerto 9991)...")
    messaging.send_json("127.0.0.1", 9991, task_payload)
    
    time.sleep(2)
    messaging.stop()

if __name__ == "__main__":
    send_test_task()