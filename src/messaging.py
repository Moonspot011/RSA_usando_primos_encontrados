import socket
import json
import threading
import logging

class MessageService:
    """Envía y recibe mensajes JSON sobre Sockets UDP de forma no bloqueante."""
    
    def __init__(self, host, port, on_message_callback):
        self.host = host
        self.port = port
        self.on_message_callback = on_message_callback
        self.running = False
        self.socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def start(self):
        self.running = True
        self.socket_udp.bind((self.host, self.port))
        
        # Hilo secundario para escuchar mensajes sin congelar el programa
        thread = threading.Thread(target=self._listen_loop, daemon=True)
        thread.start()

    def _listen_loop(self):
        while self.running:
            try:
                data, addr = self.socket_udp.recvfrom(4096)
                message = json.loads(data.decode('utf-8'))
                self.on_message_callback(message, addr)
            except Exception:
                if not self.running:
                    break

    def send_json(self, dest_ip, dest_port, message_dict):
        try:
            payload = json.dumps(message_dict).encode('utf-8')
            self.socket_udp.sendto(payload, (dest_ip, dest_port))
        except Exception as e:
            logging.error(f"Error enviando mensaje UDP a {dest_ip}:{dest_port} -> {e}")

    def stop(self):
        self.running = False
        self.socket_udp.close()