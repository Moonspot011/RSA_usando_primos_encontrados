import sys
import time
import threading
from src.messaging import MessageService
from src.crypto.cryptosystems import crear_cripto
import os

NODE_PORT = 9991
ALGO = os.environ.get("CRYPTO_ALGO", "rsa")

def send_test_task(cifrado=True):
    # El cliente también tiene su propio par de llaves (para recibir el resultado cifrado)
    crypto = crear_cripto(ALGO)
    node_key = {}
    got_key, got_result = threading.Event(), threading.Event()

    def on_message(msg, addr):
        msg_type = msg["header"]["type"]
        if msg_type == "PUBKEY_RESPONSE":
            node_key["key"] = msg["payload"]["public_key"]
            got_key.set()
        elif msg_type == "TASK_RESULT":
            print(f"<-- Resultado recibido (cifrado={msg['header']['secure']}): {msg['payload']['result_data']}")
            got_result.set()

    # Nos conectamos como un cliente temporal en el puerto 9999
    messaging = MessageService("127.0.0.1", 9999, on_message, crypto)
    messaging.start()
    time.sleep(1)

    task_payload = {
        "header": {
            "sender_id": "cliente-prueba",
            "type": "TASK_SUBMIT",
            "timestamp": time.time()
        },
        "payload": {
            "task_id": "task-101",
            "task_name": "regresion_lineal",
            "parameters": {"dataset": "ventas_2026", "learning_rate": 0.05},
            "reply_public_key": crypto.public_key()
        }
    }

    if not cifrado:
        print("--> Enviando tarea SIN CIFRAR (el nodo debe rechazarla)...")
        messaging.send_json("127.0.0.1", NODE_PORT, task_payload)
        time.sleep(2)
        messaging.stop()
        return

    # 1. Handshake: pedir la clave pública del nodo
    print(f"--> Pidiendo clave pública a nodo-01 (puerto {NODE_PORT})...")
    request = {"header": {"sender_id": "cliente-prueba", "type": "PUBKEY_REQUEST", "timestamp": time.time()},
               "payload": {}}
    messaging.send_json("127.0.0.1", NODE_PORT, request)
    if not got_key.wait(3):
        print("No se recibió la clave pública del nodo. ¿Está corriendo run_node.py?")
        messaging.stop()
        return

    # 2. Enviar la tarea cifrada con la clave pública del nodo
    print(f"--> Enviando tarea de prueba CIFRADA ({ALGO.upper()}) a nodo-01 (puerto {NODE_PORT})...")
    messaging.send_secure("127.0.0.1", NODE_PORT, task_payload, node_key["key"])

    if not got_result.wait(5):
        print("No llegó el resultado de la tarea.")
    messaging.stop()

if __name__ == "__main__":
    send_test_task(cifrado="--plano" not in sys.argv)
