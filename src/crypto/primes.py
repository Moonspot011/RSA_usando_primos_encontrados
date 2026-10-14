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


# Estado del LCG: se siembra UNA vez con la estampa de tiempo y luego avanza en cada llamada.
_LCG_A = 6364136223846793005    # multiplicador (a ≡ 1 mod 4)
_LCG_C = 1442695040888963407    # incremento impar  -> periodo completo con módulo 2^k (Hull-Dobell)
_LCG_M = 2 ** 136               # módulo > 10^40, así cubre todo el rango de 40 dígitos
_estado_lcg = None


def generar_tecnica_3(digitos=DIGITOS_PRIMO):
    """
    TÉCNICA 3: Generador Congruencial Lineal (LCG) sembrado con la estampa de tiempo.
    X(n+1) = (a * X(n) + c) mod m   con m = 2^136.
    El estado se siembra una vez con time.time_ns() y avanza en cada llamada.
    """
    global _estado_lcg
    if _estado_lcg is None:
        _estado_lcg = time.time_ns() % _LCG_M
        for _ in range(20):  # calentamiento: el estado inicial es pequeño y aún no "llena" los 136 bits
            _estado_lcg = (_LCG_A * _estado_lcg + _LCG_C) % _LCG_M

    _estado_lcg = (_LCG_A * _estado_lcg + _LCG_C) % _LCG_M

    minimo = 10 ** (digitos - 1)
    rango = 10 ** digitos - minimo  # 9 * 10^(digitos-1) valores posibles
    return minimo + _estado_lcg % rango