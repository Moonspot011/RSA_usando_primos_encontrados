"""
Criptosistemas RSA y ElGamal (portados del notebook, bloques 3 y 4).

A diferencia del notebook, que cifra el mensaje como un solo entero (límite de
~33 bytes con RSA y ~16 con ElGamal), aquí el mensaje se parte en bloques para
poder cifrar mensajes JSON completos entre nodos.

OJO: con primos de 40 dígitos las llaves son DIDÁCTICAS (se factorizan en
segundos). Para producción usar llaves de 2048+ bits y relleno OAEP.
"""
import math
import random

from src.crypto.primes import generar_primo, DIGITOS_PRIMO

_rng = random.SystemRandom()


def _fuente_aleatoria(digitos):
    """Fuente de primos por defecto: genera primos nuevos con Miller-Rabin."""
    while True:
        yield generar_primo(digitos)


MARCADOR = b"\x01"  # byte inicial de cada bloque: evita perder ceros a la izquierda


def _bytes_por_bloque(modulo):
    """Bytes de datos por bloque, de modo que MARCADOR+datos < modulo."""
    return (modulo.bit_length() - 1) // 8 - 1


def _partir(datos, tam):
    for i in range(0, len(datos), tam):
        yield datos[i:i + tam]


def _a_entero(trozo):
    return int.from_bytes(MARCADOR + trozo, "big")


def _a_bytes(m):
    crudo = m.to_bytes((m.bit_length() + 7) // 8, "big")
    if crudo[:1] != MARCADOR:
        raise ValueError("Bloque corrupto o llave incorrecta")
    return crudo[1:]


class RSA:
    """
    Llaves: N = p*q, e = 65537, d = e^-1 mod phi(N)
    Cifrar:    C = M^e mod N      Descifrar: M = C^d mod N
    """
    algo = "rsa"

    def __init__(self, digitos=DIGITOS_PRIMO, fuente=None):
        # `fuente` es un iterador de primos (p. ej. el lote de primos hallados)
        fuente = fuente if fuente is not None else _fuente_aleatoria(digitos)
        e = 65537
        while True:
            p, q = next(fuente), next(fuente)
            phi = (p - 1) * (q - 1)
            if p != q and math.gcd(e, phi) == 1:
                break
        self.n = p * q
        self.e = e
        self._d = pow(e, -1, phi)  # clave privada

    def public_key(self):
        return {"algo": self.algo, "e": self.e, "n": self.n}

    @staticmethod
    def encrypt(clave_publica, datos):
        e, n = clave_publica["e"], clave_publica["n"]
        tam = _bytes_por_bloque(n)
        bloques = [pow(_a_entero(t), e, n) for t in _partir(datos, tam)]
        return {"algo": "rsa", "blocks": bloques}

    def decrypt(self, cifrado):
        return b"".join(_a_bytes(pow(c, self._d, self.n)) for c in cifrado["blocks"])


class ElGamal:
    """
    Llaves: primo p, generador g=2, privada x, pública y = g^x mod p
    Cifrar:    k aleatorio; C1 = g^k mod p ; C2 = M * y^k mod p
    Descifrar: s = C1^x mod p ; M = C2 * s^-1 mod p
    """
    algo = "elgamal"

    def __init__(self, digitos=DIGITOS_PRIMO, fuente=None):
        fuente = fuente if fuente is not None else _fuente_aleatoria(digitos)
        self.p = next(fuente)
        self.g = 2
        self._x = _rng.randint(2, self.p - 2)  # clave privada
        self.y = pow(self.g, self._x, self.p)

    def public_key(self):
        return {"algo": self.algo, "p": self.p, "g": self.g, "y": self.y}

    @staticmethod
    def encrypt(clave_publica, datos):
        p, g, y = clave_publica["p"], clave_publica["g"], clave_publica["y"]
        tam = _bytes_por_bloque(p)
        bloques = []
        for trozo in _partir(datos, tam):
            k = _rng.randint(2, p - 2)  # clave efímera distinta por bloque
            c1 = pow(g, k, p)
            c2 = (_a_entero(trozo) * pow(y, k, p)) % p
            bloques.append([c1, c2])
        return {"algo": "elgamal", "blocks": bloques}

    def decrypt(self, cifrado):
        salida = b""
        for c1, c2 in cifrado["blocks"]:
            s = pow(c1, self._x, self.p)
            salida += _a_bytes((c2 * pow(s, -1, self.p)) % self.p)
        return salida


ALGORITMOS = {"rsa": RSA, "elgamal": ElGamal}


def crear_cripto(algo="rsa", digitos=DIGITOS_PRIMO, fuente=None):
    """
    Crea un criptosistema con un par de llaves nuevo ('rsa' o 'elgamal').
    Si se pasa `fuente` (iterador de primos), p y q se toman de ahí; si no, se generan.
    """
    clase = ALGORITMOS.get(str(algo).lower())
    if clase is None:
        raise ValueError(f"Algoritmo desconocido '{algo}'. Usa: {list(ALGORITMOS)}")
    return clase(digitos, fuente)


def cifrar_para(clave_publica, datos):
    """Cifra `datos` (bytes) con la clave pública de otro nodo (según su 'algo')."""
    clase = ALGORITMOS.get(clave_publica.get("algo"))
    if clase is None:
        raise ValueError("Clave pública con algoritmo no soportado")
    return clase.encrypt(clave_publica, datos)