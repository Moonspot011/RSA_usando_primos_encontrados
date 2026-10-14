# Red distribuida de nodos con reparto de tareas de IA y comunicación cifrada

Sistema que (1) genera números pseudoaleatorios de 40 cifras con 3 técnicas, (2) halla cuáles son primos, (3) usa esos primos como llaves **RSA o ElGamal** y (4) los aplica a una red de 3 nodos que se descubren entre sí, se reparten tareas de IA y se comunican **cifrados**.

> **Nota:** las llaves de 40 dígitos (~260 bits) son **didácticas**. Se factorizan en segundos; para un uso real se necesitan llaves de 2048 bits o más y relleno OAEP.

## Cumplimiento del enunciado

| Requisito | Dónde está |
|---|---|
| Máquina con parámetros que genera un número pseudoaleatorio de 40 cifras | `generador_primos.py` (`--digitos`, `--tecnica`, `--cantidad`) |
| Al menos 3 técnicas diferentes | `src/crypto/primes.py`: `randint`, cadena de dígitos y LCG sembrado con la hora |
| Generar 10.000 números de 40 cifras y hallar los primos | `python generador_primos.py` → guarda los primos en `primos.txt` |
| Sistema de encriptación usando los primos encontrados | `src/crypto/cryptosystems.py` (RSA y ElGamal) + `src/crypto/lote.py` (los nodos toman p y q de `primos.txt`) |
| Pruebas de encriptación | `tests/test_cifrado.py` (35 pruebas) y `reporte_pruebas.txt` |

## Estructura del proyecto

```
project/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── conftest.py              # Permite que pytest importe `src`
├── run_node.py              # Arranca un nodo
├── generador_primos.py      # Máquina: genera números, halla los primos y los guarda
├── primos.txt               # Lote de primos hallados (salida del generador)
├── test_send_task.py        # Cliente de prueba (Tx) que envía una tarea cifrada
├── reporte_pruebas.txt      # Resultado de las pruebas (pytest -v)
├── tests/
│   └── test_cifrado.py      # Pruebas de números, lote, selección y encriptación
└── src/
    ├── crypto/
    │   ├── primes.py            # Miller-Rabin, generador de primos y las 3 técnicas
    │   ├── lote.py              # Guardar/cargar primos.txt y selección por fecha
    │   └── cryptosystems.py     # RSA y ElGamal (cifrado por bloques)
    ├── inference/
    │   └── ai_worker.py         # Ejecuta la "inferencia" (simulada)
    ├── discovery.py         # Descubrimiento, beacons y detección de fallos
    ├── messaging.py         # UDP + JSON, cifrado/descifrado transparente
    ├── models.py            # NodeInfo y Task
    ├── node.py              # Une todos los servicios de un nodo
    ├── resource_manager.py  # CPU y RAM libres (psutil)
    ├── scheduler.py         # Elige el mejor nodo (función de aptitud)
    └── task_manager.py      # Envío de tareas y reasignación ante fallos
```

## Requisitos

- Python 3.8 o superior (el Dockerfile usa 3.10)
- `psutil` y `pytest` (ver `requirements.txt`)

```bash
pip install -r requirements.txt
```

## Ejecución

Todos los comandos se ejecutan desde la raíz del proyecto. En Windows usa `python`; en Linux/macOS puede ser `python3`.

### 1. Generar los números y hallar los primos

```bash
python generador_primos.py
```

Genera 10.000 números de 40 cifras repartidos entre las 3 técnicas, evalúa su primalidad en paralelo y guarda los primos hallados en `primos.txt`. Salida de ejemplo:

```
 Números generados           : 10000 (de 40 cifras)
 Números primos hallados     : 96
   - cadena_texto : 34
   - lcg_tiempo   : 28
   - randint      : 34
 Primos guardados en 'primos.txt'
```

Parámetros disponibles:

| Parámetro | Descripción | Por defecto |
|---|---|---|
| `--tecnica` | `1` (randint), `2` (cadena de dígitos), `3` (LCG con hora) o `todas` | `todas` |
| `--digitos` | Cifras de cada número | `40` |
| `--cantidad` | Cuántos números generar | `10000` |
| `--salida` | Archivo donde se guardan los primos | `primos.txt` |
| `--mostrar` | Cuántos primos imprimir en pantalla | `10` |

```bash
python generador_primos.py --tecnica 3 --cantidad 500 --salida prueba.txt
python generador_primos.py --cantidad 100000     # lote más grande (≈1000 primos)
```

### 2. Levantar la red de 3 nodos

Abre **3 terminales**, una por nodo:

```bash
python run_node.py nodo-01 9991
python run_node.py nodo-02 9992
python run_node.py nodo-03 9993
```

Al iniciar, cada nodo toma sus primos de `primos.txt`:

```
[CRYPTO] Nodo nodo-01: llaves RSA con primos del lote de 96 primos, semilla 202610140231-nodo-01
[DISCOVERY] Nuevo nodo descubierto: nodo-02 en puerto 9992
```

Si `primos.txt` no existe o tiene menos de 10 primos, el nodo avisa con un `WARNING` y genera sus primos al vuelo (con Miller-Rabin).

### 3. Enviar una tarea cifrada

En una cuarta terminal:

```bash
python test_send_task.py
```

```
--> Pidiendo clave pública a nodo-01 (puerto 9991)...
--> Enviando tarea de prueba CIFRADA (RSA) a nodo-01 (puerto 9991)...
<-- Resultado recibido (cifrado=True): {'slope': 2.35, 'intercept': 0.81, 'mse': 0.04}
```

Para comprobar que un mensaje sin cifrar se rechaza:

```bash
python test_send_task.py --plano
# nodo-01: [CRYPTO] TASK_SUBMIT de cliente-prueba RECHAZADO: llegó sin cifrar
```

### 4. Elegir el algoritmo (RSA o ElGamal)

Con la variable de entorno `CRYPTO_ALGO` (por defecto `rsa`), definida al iniciar cada nodo. Cada nodo puede usar uno distinto: quien cifra usa el algoritmo indicado en la clave pública del destinatario.

```bash
# Linux / macOS
CRYPTO_ALGO=elgamal python run_node.py nodo-01 9991

# Windows (PowerShell)
$env:CRYPTO_ALGO="elgamal"; python run_node.py nodo-01 9991
```

Para usar otro archivo de primos: variable `PRIMOS_FILE` (por defecto `primos.txt`).

### 5. Pruebas de encriptación

```bash
python -m pytest tests -v
python -m pytest tests -v > reporte_pruebas.txt     # guardar el reporte
```

Las 35 pruebas cubren:
- las 3 técnicas (40 cifras, sin repetidos, sin quedar pegadas a un rango) y Miller-Rabin con valores conocidos (incluido el número de Carmichael 561);
- guardar y cargar el lote, y la selección de primos por fecha;
- cifrado y descifrado de **números** (0, 1, 2⁶⁴, 10³⁹, primos del lote) y de **mensajes** (tildes, emojis, 2000 caracteres, JSON) con RSA y ElGamal;
- que una llave equivocada o un mensaje alterado no recuperen el original;
- el envío cifrado por UDP entre dos servicios, y que un mensaje en claro no pueda declararse seguro.

### 6. Con Docker

```bash
docker-compose up --build
```

Levanta los 3 nodos con `network_mode: host` (nativo en Linux). El `Dockerfile` hace `COPY . .`, así que `primos.txt` viaja dentro de la imagen: regenera el lote **antes** de construir. Para ElGamal agrega en cada servicio del `docker-compose.yml`:

```yaml
    environment:
      - CRYPTO_ALGO=elgamal
```

## Cómo funciona

### Selección de los primos de cada nodo

Los nodos eligen sus primos del lote usando la fecha como semilla "aleatoria":

```
semilla = AÑO MES DÍA HORA MINUTO + "-" + node_id        ej: 202610140231-nodo-01
índice  = SHA-256(semilla : contador) mod tamaño_del_lote
```

- Se toman primos sucesivos (sin repetir) hasta tener los que necesita el algoritmo: **p y q** para RSA, **p** para ElGamal. En RSA, si `e = 65537` no es coprimo con φ(N), se pasa al siguiente par.
- Se incluye el `node_id` para que dos nodos iniciados en el mismo minuto **no obtengan los mismos primos** (tendrían la misma llave privada y cada uno podría leer los mensajes del otro).
- Misma fecha y mismo nodo → mismas llaves (reproducible). Reiniciar el nodo en otro minuto genera llaves nuevas, que los demás actualizan con el siguiente beacon.
- Se usa SHA-256 para repartir bien los índices: minutos consecutivos darían semillas casi iguales y, sin la función hash, elecciones casi iguales.

### Generación de números y primos

Las 3 técnicas producen números de `--digitos` cifras:

1. **randint:** `random.randint` (Mersenne Twister) en el rango `[10^(d-1), 10^d - 1]`.
2. **cadena de dígitos:** primer dígito 1-9 y el resto 0-9 elegidos uno a uno.
3. **LCG:** `X(n+1) = (a·X(n) + c) mod 2^136`, sembrado una vez con `time.time_ns()` y con un calentamiento inicial. Cada llamada avanza el estado.

La primalidad se decide con un filtro de primos pequeños y **Miller-Rabin** (15 rondas). De 10.000 números de 40 cifras se esperan unos 108 primos (densidad ≈ 1/ln(10⁴⁰) ≈ 1/92).

### Descubrimiento, planificación y tolerancia a fallos
- Cada nodo envía un **beacon** (`RESOURCE_BEACON`) cada 2 s con su CPU libre, RAM libre y su **clave pública**.
- Sin beacons durante más de 5 s, el nodo pasa a `OFFLINE`; si el nodo que ejecutaba una tarea cae, el `TaskManager` la reasigna.
- El `DistributedScheduler` elige entre los nodos `ONLINE` que cumplan los requisitos con la función de aptitud: CPU libre 40 %, RAM libre 40 %, ancho de banda 10 %, reputación 5 %, latencia 5 % (los tres últimos simulados).

### Criptosistemas

**RSA:** `N = p·q`, `e = 65537`, `d = e⁻¹ mod φ(N)`. Cifrar: `C = Mᵉ mod N`. Descifrar: `M = Cᵈ mod N`.

**ElGamal:** primo `p`, generador `g = 2`, clave privada `x`, pública `y = gˣ mod p`. Cifrar con `k` aleatorio por bloque: `C₁ = gᵏ mod p`, `C₂ = M·yᵏ mod p`. Descifrar: `M = C₂ · (C₁ˣ)⁻¹ mod p`.

**Cifrado por bloques:** el mensaje JSON se convierte a bytes y se parte en bloques que quepan en el módulo (31 bytes con RSA, 15 con ElGamal). Cada bloque lleva un byte marcador `0x01` al inicio para no perder ceros a la izquierda al pasar a entero.

### Tipos de mensaje

| Tipo | Cifrado | Descripción |
|---|---|---|
| `RESOURCE_BEACON` | No | Recursos del nodo + clave pública |
| `PUBKEY_REQUEST` / `PUBKEY_RESPONSE` | No | Handshake para que un cliente externo obtenga la clave pública de un nodo |
| `TASK_SUBMIT` | **Sí** | Envío de una tarea de IA |
| `TASK_RESULT` | **Sí** | Resultado de la tarea |
| `ENCRYPTED` | — | Sobre que envuelve a cualquier mensaje cifrado |

`MessageService` cifra y descifra de forma transparente: el resto del código recibe los mensajes ya descifrados con `header["secure"] = True`. Los mensajes que llegan en claro siempre se marcan `secure = False`, así que no pueden hacerse pasar por seguros.

### Flujo de una tarea (Tx → Rx)

```
Cliente (Tx)                                  Nodo (Rx)
    │── PUBKEY_REQUEST ───────────────────────▶│
    │◀───────────────────── PUBKEY_RESPONSE ───│  (clave pública del nodo)
    │                                          │
    │── ENCRYPTED(TASK_SUBMIT) ───────────────▶│  cifrado con la clave pública del nodo
    │                                          │  descifra con su clave privada
    │                                          │  ejecuta la inferencia
    │◀────────────── ENCRYPTED(TASK_RESULT) ───│  cifrado con la clave pública del cliente
```

## Limitaciones conocidas

- **El lote es pequeño y público** (~100 primos): quien tenga `primos.txt` puede probar todos los pares y factorizar cualquier N. Además, dos nodos podrían elegir un mismo primo (con 96 primos y 3 nodos, ~12 % de probabilidad); en RSA eso permitiría a uno calcular la llave privada del otro con `gcd(N₁, N₂)`. Un lote mayor (`--cantidad 100000`) baja esa probabilidad a ~1 %.
- La semilla por fecha tiene resolución de minuto y es predecible: sirve para el enunciado, no como fuente de aleatoriedad criptográfica.
- Los beacons **no están firmados**: un atacante activo podría hacerse pasar por un nodo publicando su propia clave.
- RSA "de libro" sin relleno OAEP y ElGamal con `g = 2` sobre un primo no seguro; suficiente para fines académicos.
- La inferencia (`ai_worker.py`) es simulada: devuelve resultados fijos. Ancho de banda, reputación y latencia del scheduler son valores constantes.