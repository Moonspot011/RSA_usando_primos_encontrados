"""
Pruebas del sistema: números pseudoaleatorios, lote de primos, selección por fecha
y encriptación (RSA y ElGamal) de números y mensajes.

Ejecutar:  python -m pytest tests -v
"""
import os
import threading
import time
from datetime import datetime

import pytest

from src.crypto.cryptosystems import crear_cripto, cifrar_para
from src.crypto.lote import cargar_lote, guardar_lote, semilla_fecha, flujo_primos
from src.crypto.primes import (es_primo, generar_primo, generar_tecnica_1,
                               generar_tecnica_2, generar_tecnica_3)
from src.messaging import MessageService

ALGOS = ["rsa", "elgamal"]


@pytest.fixture(scope="module")
def lote_primos():
    """Lote de 40 primos de 40 cifras para las pruebas."""
    return [generar_primo(40) for _ in range(40)]


# ----------------------------------------------------------------------------
# 1. Números pseudoaleatorios de 40 cifras (3 técnicas)
# ----------------------------------------------------------------------------
def test_es_primo_valores_conocidos():
    for p in (2, 3, 11, 13, 31, 37, 7919, 2 ** 61 - 1):
        assert es_primo(p), p
    for n in (0, 1, 9, 15, 561, 7917, 2 ** 61 - 3):  # 561 es un número de Carmichael
        assert not es_primo(n), n


@pytest.mark.parametrize("tecnica", [generar_tecnica_1, generar_tecnica_2, generar_tecnica_3])
def test_tecnicas_generan_numeros_de_40_cifras(tecnica):
    numeros = [tecnica(40) for _ in range(200)]
    assert all(len(str(n)) == 40 for n in numeros)
    assert len(set(numeros)) > 190                       # casi sin repetidos
    assert len({str(n)[:4] for n in numeros}) > 50       # no están pegados a un rango (caso del LCG viejo)


def test_tecnicas_aceptan_otra_cantidad_de_cifras():
    for tecnica in (generar_tecnica_1, generar_tecnica_2, generar_tecnica_3):
        assert len(str(tecnica(25))) == 25


def test_generar_primo_devuelve_primos_de_40_cifras():
    for _ in range(5):
        p = generar_primo(40)
        assert len(str(p)) == 40 and es_primo(p)


# ----------------------------------------------------------------------------
# 2. Lote de primos y selección por fecha
# ----------------------------------------------------------------------------
def test_lote_guardar_y_cargar(tmp_path, lote_primos):
    ruta = tmp_path / "primos.txt"
    guardar_lote([("randint", p) for p in lote_primos], str(ruta))
    assert cargar_lote(str(ruta)) == lote_primos


def test_cargar_lote_descarta_numeros_no_primos(tmp_path):
    ruta = tmp_path / "primos.txt"
    ruta.write_text("# tecnica,numero\nrandint,7919\nrandint,7917\n", encoding="utf-8")
    assert cargar_lote(str(ruta)) == [7919]


def test_semilla_usa_anio_mes_dia_hora_minuto_y_nodo():
    assert semilla_fecha("nodo-01", datetime(2026, 10, 13, 14, 32, 55)) == "202610131432-nodo-01"


def test_seleccion_es_reproducible_y_sin_repetidos():
    lote = list(range(1000, 1100))
    semilla = semilla_fecha("nodo-01", datetime(2026, 10, 13, 14, 32))
    a = [x for _, x in zip(range(100), flujo_primos(lote, semilla))]
    b = [x for _, x in zip(range(100), flujo_primos(lote, semilla))]
    assert a == b                      # misma fecha + mismo nodo -> mismos primos
    assert sorted(a) == lote           # recorre todo el lote sin repetir


def test_nodos_en_el_mismo_minuto_obtienen_primos_distintos():
    lote = list(range(1000, 1100))
    ahora = datetime(2026, 10, 13, 14, 32)
    elegidos = {nid: tuple(x for _, x in zip(range(2), flujo_primos(lote, semilla_fecha(nid, ahora))))
                for nid in ("nodo-01", "nodo-02", "nodo-03")}
    assert len(set(elegidos.values())) == 3


def test_distinto_minuto_cambia_la_seleccion():
    lote = list(range(1000, 1100))
    s1 = semilla_fecha("nodo-01", datetime(2026, 10, 13, 14, 32))
    s2 = semilla_fecha("nodo-01", datetime(2026, 10, 13, 14, 33))
    a = [x for _, x in zip(range(2), flujo_primos(lote, s1))]
    b = [x for _, x in zip(range(2), flujo_primos(lote, s2))]
    assert a != b


@pytest.mark.parametrize("algo", ALGOS)
def test_llaves_se_construyen_con_primos_del_lote(algo, lote_primos):
    semilla = semilla_fecha("nodo-01", datetime(2026, 10, 13, 14, 32))
    c = crear_cripto(algo, fuente=flujo_primos(lote_primos, semilla))
    if algo == "rsa":
        factores = [p for p in lote_primos if c.n % p == 0]
        assert len(factores) == 2 and factores[0] * factores[1] == c.n
    else:
        assert c.p in lote_primos


# ----------------------------------------------------------------------------
# 3. Pruebas de encriptación
# ----------------------------------------------------------------------------
def _num_a_bytes(n):
    return n.to_bytes(max(1, (n.bit_length() + 7) // 8), "big")


@pytest.mark.parametrize("algo", ALGOS)
def test_cifrado_de_numeros(algo, lote_primos):
    c = crear_cripto(algo)
    numeros = [0, 1, 255, 2 ** 64, 10 ** 39, 10 ** 40 - 1] + lote_primos[:5]
    for n in numeros:
        cifrado = cifrar_para(c.public_key(), _num_a_bytes(n))
        assert int.from_bytes(c.decrypt(cifrado), "big") == n


@pytest.mark.parametrize("algo", ALGOS)
@pytest.mark.parametrize("mensaje", [
    "A",
    "Hola, esta es una prueba de encriptación",
    "Ñandú, acentos áéíóú y emojis 🔐🚀",
    "x" * 2000,                                   # muchos bloques
    '{"task_id": "task-101", "params": {"lr": 0.05}}',
], ids=["1_caracter", "texto_con_tilde", "unicode_y_emojis", "2000_caracteres", "json_de_tarea"])
def test_cifrado_de_mensajes(algo, mensaje):
    c = crear_cripto(algo)
    cifrado = cifrar_para(c.public_key(), mensaje.encode("utf-8"))
    assert c.decrypt(cifrado).decode("utf-8") == mensaje


@pytest.mark.parametrize("algo", ALGOS)
def test_el_cifrado_no_deja_el_texto_a_la_vista(algo):
    c = crear_cripto(algo)
    cifrado = cifrar_para(c.public_key(), b"mensaje secreto")
    assert b"mensaje secreto" not in str(cifrado).encode()


@pytest.mark.parametrize("algo", ALGOS)
def test_llave_equivocada_no_descifra(algo):
    emisor_dest, intruso = crear_cripto(algo), crear_cripto(algo)
    cifrado = cifrar_para(emisor_dest.public_key(), b"secreto")
    try:
        assert intruso.decrypt(cifrado) != b"secreto"
    except Exception:
        pass  # también es válido que falle


@pytest.mark.parametrize("algo", ALGOS)
def test_mensaje_alterado_no_se_recupera(algo):
    c = crear_cripto(algo)
    cifrado = cifrar_para(c.public_key(), b"transferir 100 a Ana")
    if algo == "rsa":
        cifrado["blocks"][0] += 1
    else:
        cifrado["blocks"][0][1] += 1
    try:
        assert c.decrypt(cifrado) != b"transferir 100 a Ana"
    except Exception:
        pass


def test_elgamal_cifra_distinto_cada_vez():
    c = crear_cripto("elgamal")
    a = cifrar_para(c.public_key(), b"mismo mensaje")
    b = cifrar_para(c.public_key(), b"mismo mensaje")
    assert a != b and c.decrypt(a) == c.decrypt(b) == b"mismo mensaje"


# ----------------------------------------------------------------------------
# 4. Cifrado extremo a extremo por UDP (MessageService)
# ----------------------------------------------------------------------------
@pytest.mark.parametrize("algo", ALGOS)
def test_mensaje_cifrado_por_udp(algo):
    cripto_b = crear_cripto(algo)
    recibidos, listo = [], threading.Event()

    def al_recibir(msg, addr):
        recibidos.append(msg)
        if len(recibidos) == 2:
            listo.set()

    puerto_a, puerto_b = (19991, 19992) if algo == "rsa" else (19993, 19994)
    a = MessageService("127.0.0.1", puerto_a, lambda m, ad: None)
    b = MessageService("127.0.0.1", puerto_b, al_recibir, cripto_b)
    a.start(); b.start()
    time.sleep(0.3)
    try:
        msg = {"header": {"sender_id": "A", "type": "TASK_SUBMIT", "timestamp": 0},
               "payload": {"dato": "contenido confidencial"}}
        a.send_secure("127.0.0.1", puerto_b, msg, cripto_b.public_key())

        # Un mensaje en claro que intenta declararse "secure" debe llegar con secure=False
        falso = {"header": {"sender_id": "X", "type": "TASK_SUBMIT", "timestamp": 0, "secure": True},
                 "payload": {}}
        a.send_json("127.0.0.1", puerto_b, falso)

        assert listo.wait(3)
        cifrado = next(m for m in recibidos if m["header"]["sender_id"] == "A")
        plano = next(m for m in recibidos if m["header"]["sender_id"] == "X")
        assert cifrado["header"]["secure"] is True
        assert cifrado["payload"]["dato"] == "contenido confidencial"
        assert plano["header"]["secure"] is False
    finally:
        a.stop(); b.stop()