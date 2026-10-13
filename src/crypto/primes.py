"""
Generación y verificación de números primos grandes.
Portado del notebook `numeros_aleatorios.ipynb` (bloques 1 y 2).
"""
import random
import time

DIGITOS_PRIMO = 40  # tamaño de los primos usados para las llaves: [10^39, 10^40 - 1]

# Generador criptográficamente seguro (usa os.urandom). Se usa para las llaves reales.
_rng = random.SystemRandom()

PRIMOS_PEQUENOS = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31)


def es_primo(n, rondas=15):
    """
    Verifica si n es primo:
    1. Filtro rápido de división con primos pequeños.
    2. Test probabilístico de Miller-Rabin con bases elegidas al azar.
    """
    if n < 2:
        return False
    if n in PRIMOS_PEQUENOS:
        return True
    if any(n % p == 0 for p in PRIMOS_PEQUENOS):
        return False

    # Descomponer n - 1 = 2^s * d
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1

    for _ in range(rondas):
        a = _rng.randint(2, n - 2)
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def generar_primo(digitos=DIGITOS_PRIMO):
    """Genera un primo aleatorio de `digitos` dígitos (para las llaves de los nodos)."""
    minimo = 10 ** (digitos - 1)
    maximo = 10 ** digitos - 1
    while True:
        candidato = _rng.randint(minimo, maximo) | 1  # solo impares
        if es_primo(candidato):
            return candidato


# -----------------------------------------------------------------------------
# Las 3 técnicas de generación del notebook (se usan en benchmark_primos.py)
# -----------------------------------------------------------------------------

def generar_tecnica_1(digitos=DIGITOS_PRIMO):
    """TÉCNICA 1: random.randint (Mersenne Twister) en el rango completo."""
    return random.randint(10 ** (digitos - 1), 10 ** digitos - 1)


def generar_tecnica_2(digitos=DIGITOS_PRIMO):
    """TÉCNICA 2: cadena de dígitos (primer dígito 1-9 + el resto 0-9)."""
    primero = random.choice("123456789")
    resto = "".join(random.choice("0123456789") for _ in range(digitos - 1))
    return int(primero + resto)


_contador_lcg = 0


def generar_tecnica_3(digitos=DIGITOS_PRIMO):
    """
    TÉCNICA 3: Generador Congruencial Lineal sobre la estampa de tiempo.
    X(n+1) = (a * X(n) + c) mod m  con a=1103515245, c=12345, m=2^31.
    """
    global _contador_lcg
    _contador_lcg += 1

    semilla = int(time.time() * 1000) + _contador_lcg
    semilla = (semilla * 1103515245 + 12345) % (2 ** 31)

    minimo = 10 ** (digitos - 1)
    rango = (10 ** digitos - 1) - minimo
    return minimo + (semilla * 999999999) % rango
