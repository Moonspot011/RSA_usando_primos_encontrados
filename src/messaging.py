import socket
import json
import threading
import logging
import time
from src.crypto.cryptosystems import cifrar_para

class MessageService:
    """Envía y recibe mensajes JSON sobre Sockets UDP de forma no bloqueante.

    Si se le pasa `crypto` (RSA/ElGamal) puede recibir mensajes cifrados
    (type "ENCRYPTED") y los entrega ya descifrados al callback, con
    header["secure"] = True. Los mensajes en claro llegan con secure = False.
    """
    
    def __init__(self, host, port, on_message_callback, crypto=None):
        self.host = host
        self.port = port
        self.on_message_callback = on_message_callback
        self.crypto = crypto
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
                data, addr = self.socket_udp.recvfrom(65535)
                message = json.loads(data.decode('utf-8'))

                if message["header"]["type"] == "ENCRYPTED":
                    message = self._decrypt_message(message, addr)
                    if message is None:
                        continue
                    message["header"]["secure"] = True
                else:
                    # Se fuerza a False: un mensaje en claro no puede declararse seguro
                    message["header"]["secure"] = False

                self.on_message_callback(message, addr)
            except Exception:
                if not self.running:
                    break

    def _decrypt_message(self, envelope, addr):
        """Descifra un mensaje ENCRYPTED con la clave privada local. None si falla."""
        if self.crypto is None:
            logging.warning(f"[CRYPTO] Mensaje cifrado de {addr} descartado: este servicio no tiene llaves")
            return None
        try:
            inner = json.loads(self.crypto.decrypt(envelope["payload"]).decode('utf-8'))
            logging.info(f"[CRYPTO] Mensaje {inner['header']['type']} de {inner['header']['sender_id']} "
                         f"descifrado ({self.crypto.algo.upper()})")
            return inner
        except Exception as e:
            logging.warning(f"[CRYPTO] No se pudo descifrar mensaje de {addr}: {e}")
            return None

    def send_json(self, dest_ip, dest_port, message_dict):
        try:
            payload = json.dumps(message_dict).encode('utf-8')
            self.socket_udp.sendto(payload, (dest_ip, dest_port))
        except Exception as e:
            logging.error(f"Error enviando mensaje UDP a {dest_ip}:{dest_port} -> {e}")

    def send_secure(self, dest_ip, dest_port, message_dict, public_key):
        """Cifra el mensaje completo con la clave pública del destino y lo envía."""
        try:
            plain = json.dumps(message_dict).encode('utf-8')
            cifrado = cifrar_para(public_key, plain)
            envelope = {
                "header": {
                    "sender_id": message_dict["header"]["sender_id"],
                    "type": "ENCRYPTED",
                    "timestamp": time.time()
                },
                "payload": cifrado
            }
            logging.info(f"[CRYPTO] Mensaje {message_dict['header']['type']} cifrado con "
                         f"{cifrado['algo'].upper()} ({len(cifrado['blocks'])} bloques) -> puerto {dest_port}")
            self.send_json(dest_ip, dest_port, envelope)
        except Exception as e:
            logging.error(f"Error cifrando mensaje para {dest_ip}:{dest_port} -> {e}")

    def stop(self):
        self.running = False
        self.socket_udp.close()
