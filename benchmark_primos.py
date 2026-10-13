"""
Benchmark de las 3 técnicas de generación de números de 40 dígitos y búsqueda
de primos en paralelo (portado de numeros_aleatorios.ipynb).

Uso:  python benchmark_primos.py [cantidad]      (por defecto 100000)
"""
import sys
import time
from multiprocessing import Pool, cpu_count
from src.crypto.primes import es_primo, generar_tecnica_1, generar_tecnica_2, generar_tecnica_3

TECNICAS = ("randint", "cadena_texto", "formula_lcg")
GENERADORES = (generar_tecnica_1, generar_tecnica_2, generar_tecnica_3)


def evaluar_numero(item):
    idx, tecnica, num = item
    return (idx, tecnica, num, es_primo(num))


if __name__ == "__main__":
    total = int(sys.argv[1]) if len(sys.argv) > 1 else 100000
    print(f"Generando y evaluando {total} números de 40 dígitos...")
    print(f"Núcleos detectados: {cpu_count()}\n")

    inicio = time.time()

    # Repartir los índices entre las 3 técnicas
    trabajo = []
    for i in range(1, total + 1):
        t = (i - 1) % 3
        trabajo.append((i, TECNICAS[t], GENERADORES[t]()))

    resultados = []
    with Pool() as pool:
        for n, res in enumerate(pool.imap_unordered(evaluar_numero, trabajo, chunksize=100), 1):
            resultados.append(res)
            if n % max(1, total // 10) == 0:
                print(f"  Evaluando primalidad: {n}/{total} ({100 * n // total}%)")

    duracion = time.time() - inicio
    primos = [r for r in resultados if r[3]]

    print("\n" + "=" * 55)
    print("                RESUMEN DE RESULTADOS")
    print("=" * 55)
    print(f" Total de números procesados : {total}")
    print(f" Números primos hallados     : {len(primos)}")
    for t in TECNICAS:
        print(f"   - {t:<13}: {sum(1 for r in primos if r[1] == t)}")
    print(f" Tiempo total transcurrido   : {round(duracion, 2)} segundos")
    print("=" * 55)

    if primos:
        print("\n MUESTRA DE PRIMOS ENCONTRADOS (máximo 5):")
        for idx, tec, num, _ in primos[:5]:
            print(f" • [ID {idx}] Vía {tec} -> {num}")
    else:
        print("\n No se hallaron números primos en el lote evaluado.")
