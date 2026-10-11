import sys
import time
from src.node import ComplexNode

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: python run_node.py <node_id> <puerto>")
        sys.exit(1)

    node_id = sys.argv[1]
    port = int(sys.argv[2])
    
    # Lista de puertos de la red de 3 nodos
    all_ports = [9991, 9992, 9993]

    node = ComplexNode(node_id, "127.0.0.1", port, all_ports)
    node.start()

    try:
        while True:
            time.sleep(1)
            node.task_manager.check_and_reassign_failed_tasks()
            
    except KeyboardInterrupt:
        node.stop()
        print("\nNodo detenido por el usuario.")