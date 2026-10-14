"""
Lote de primos hallados y selección de los primos de cada nodo.

El lote lo produce `generador_primos.py` (10.000 números de 40 cifras -> los primos
se guardan en `primos.txt`). Cada nodo toma de ahí los primos de sus llaves.

Selección "aleatoria" por fecha:
    semilla = AAAAMMDDHHMM + "-" + node_id        (año, mes, día, hora y minuto)
    índice  = SHA-256(semilla : contador) mod tamaño_del_lote
El node_id evita que dos nodos iniciados en el mismo minuto obtengan los mismos primos
(y por tanto la misma llave privada).
"""
import hashlib
import logging
import os
from datetime import datetime

from src.crypto.primes import es_primo

RUTA_LOTE_DEFECTO = "primos.txt"
MINIMO_LOTE = 10  # con menos primos el lote no sirve para elegir llaves


def guardar_lote(primos, ruta=RUTA_LOTE_DEFECTO):
    """Guarda los primos hallados, una línea por primo: `tecnica,numero`."""
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("# tecnica,numero_primo\n")
        for tecnica, numero in primos:
            f.write(f"{tecnica},{numero}\n")


def cargar_lote(ruta=RUTA_LOTE_DEFECTO, verificar=True):
    """Lee el lote. Con verificar=True descarta cualquier línea que no sea un primo."""
    lote = []
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            numero = int(linea.split(",")[-1])
            if verificar and not es_primo(numero):
                logging.warning(f"[LOTE] {numero} no es primo; se descarta")
                continue
            lote.append(numero)
    return lote


def semilla_fecha(node_id, ahora=None):
    """Semilla = año+mes+día+hora+minuto + id del nodo. Ej: 202610131432-nodo-01"""
    ahora = ahora or datetime.now()
    return ahora.strftime("%Y%m%d%H%M") + "-" + node_id


def flujo_primos(lote, semilla):
    """
    Entrega primos del lote, sin repetir, en un orden determinado por la semilla.
    Misma semilla -> mismos primos (reproducible); semilla distinta -> otros primos.
    """
    usados, contador = set(), 0
    while len(usados) < len(lote):
        h = hashlib.sha256(f"{semilla}:{contador}".encode()).digest()
        contador += 1
        i = int.from_bytes(h, "big") % len(lote)
        if i not in usados:
            usados.add(i)
            yield lote[i]


def fuente_para_nodo(node_id, ruta=None):
    """
    Devuelve (fuente_de_primos, descripcion) para el nodo, o (None, motivo)
    si no hay un lote utilizable (entonces el nodo genera sus primos solo).
    """
    ruta = ruta or os.environ.get("PRIMOS_FILE", RUTA_LOTE_DEFECTO)
    if not os.path.exists(ruta):
        return None, f"no existe '{ruta}'"
    lote = cargar_lote(ruta)
    if len(lote) < MINIMO_LOTE:
        return None, f"el lote '{ruta}' tiene solo {len(lote)} primos"
    semilla = semilla_fecha(node_id)
    return flujo_primos(lote, semilla), f"lote de {len(lote)} primos, semilla {semilla}"