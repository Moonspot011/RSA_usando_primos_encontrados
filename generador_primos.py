"""
Máquina generadora de números pseudoaleatorios de N cifras y buscadora de primos.

Parámetros:
  --tecnica  1 = random.randint | 2 = cadena de dígitos | 3 = LCG con estampa de tiempo
             | todas = reparte los números entre las 3 técnicas (por defecto)
  --digitos  cifras de cada número (por defecto 40)
  --cantidad cuántos números generar (por defecto 10000)
  --salida   archivo donde se guardan los primos hallados (por defecto primos.txt)
  --mostrar  cuántos primos imprimir en pantalla (por defecto 10)

Ejemplos:
  python generador_primos.py
  python generador_primos.py --tecnica 3 --cantidad 500 --salida prueba.txt
"""
import argparse
import time
from multiprocessing import Pool, cpu_count

from src.crypto.primes import (es_primo, generar_tecnica_1, generar_tecnica_2,
                               generar_tecnica_3)
from src.crypto.lote import guardar_lote

NOMBRES = {1: "randint", 2: "cadena_texto", 3: "lcg_tiempo"}
GENERADORES = {1: generar_tecnica_1, 2: generar_tecnica_2, 3: generar_tecnica_3}


def evaluar(item):
    """Se ejecuta en paralelo: indica si el número es primo."""
    idx, tecnica, numero = item
    return idx, tecnica, numero, es_primo(numero)


def generar_numeros(tecnica, digitos, cantidad):
    """Genera `cantidad` números de `digitos` cifras. Devuelve [(id, tecnica, numero)]."""
    tecnicas = [1, 2, 3] if tecnica == "todas" else [int(tecnica)]
    return [(i, NOMBRES[tecnicas[(i - 1) % len(tecnicas)]],
             GENERADORES[tecnicas[(i - 1) % len(tecnicas)]](digitos))
            for i in range(1, cantidad + 1)]


def main():
    ap = argparse.ArgumentParser(description="Genera números pseudoaleatorios y halla los primos")
    ap.add_argument("--tecnica", choices=["1", "2", "3", "todas"], default="todas")
    ap.add_argument("--digitos", type=int, default=40)
    ap.add_argument("--cantidad", type=int, default=10000)
    ap.add_argument("--salida", default="primos.txt")
    ap.add_argument("--mostrar", type=int, default=10)
    a = ap.parse_args()

    print(f"Generando {a.cantidad} números de {a.digitos} cifras (técnica: {a.tecnica})...")
    print(f"Núcleos detectados: {cpu_count()}\n")
    inicio = time.time()

    numeros = generar_numeros(a.tecnica, a.digitos, a.cantidad)

    resultados = []
    with Pool() as pool:
        for n, r in enumerate(pool.imap_unordered(evaluar, numeros, chunksize=100), 1):
            resultados.append(r)
            if n % max(1, a.cantidad // 10) == 0:
                print(f"  Evaluando primalidad: {n}/{a.cantidad} ({100 * n // a.cantidad}%)")

    primos = sorted((r for r in resultados if r[3]), key=lambda r: r[0])
    duracion = time.time() - inicio

    print("\n" + "=" * 58)
    print("                 RESUMEN DE RESULTADOS")
    print("=" * 58)
    print(f" Números generados           : {a.cantidad} (de {a.digitos} cifras)")
    print(f" Números primos hallados     : {len(primos)}")
    for t in sorted({r[1] for r in resultados}):
        print(f"   - {t:<13}: {sum(1 for r in primos if r[1] == t)}")
    print(f" Tiempo total transcurrido   : {round(duracion, 2)} segundos")
    print("=" * 58)

    if primos:
        guardar_lote([(r[1], r[2]) for r in primos], a.salida)
        print(f"\n Primos guardados en '{a.salida}'")
        print(f"\n MUESTRA (primeros {min(a.mostrar, len(primos))}):")
        for idx, tec, num, _ in primos[:a.mostrar]:
            print(f" • [ID {idx}] {tec} -> {num}")
    else:
        print("\n No se hallaron primos en el lote evaluado.")


if __name__ == "__main__":
    main()