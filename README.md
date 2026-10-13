# Red distribuida de nodos con reparto de tareas de IA y comunicación cifrada

Sistema distribuido de 3 nodos que se descubren entre sí, se reparten tareas de IA según los recursos disponibles de cada uno y **se comunican de forma cifrada** con RSA o ElGamal, usando números primos aleatorios de 40 dígitos generados por cada nodo.

> **Nota:** las llaves de 40 dígitos (~260 bits) son **didácticas**. Se factorizan en segundos; para un uso real se necesitan llaves de 2048 bits o más y relleno OAEP.

---

## Estructura del proyecto

```
project/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── run_node.py              # Arranca un nodo
├── test_send_task.py        # Cliente de prueba (Tx) que envía una tarea cifrada
├── benchmark_primos.py      # Benchmark de las 3 técnicas de generación de números
└── src/
    ├── crypto/
    │   ├── primes.py            # Miller-Rabin, generador de primos y 3 técnicas
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

---

## Requisitos

- Python 3.8 o superior (el Dockerfile usa 3.10)
- `psutil` (ver `requirements.txt`)

```bash
pip install -r requirements.txt
```

---

## Ejecución

Todos los comandos se ejecutan desde la raíz del proyecto. En Windows usa `python`; en Linux/macOS puede ser `python3`.

### 1. Levantar la red de 3 nodos

Abre **3 terminales**, una por nodo:

```bash
python run_node.py nodo-01 9991
python run_node.py nodo-02 9992
python run_node.py nodo-03 9993
```

Al iniciar, cada nodo genera sus llaves y empieza a descubrir a los demás:

```
[CRYPTO] Nodo nodo-01: llaves RSA generadas
=== Iniciando Nodo nodo-01 en puerto 9991 ===
[DISCOVERY] Nuevo nodo descubierto: nodo-02 en puerto 9992
```

### 2. Enviar una tarea cifrada

En una cuarta terminal:

```bash
python test_send_task.py
```

Salida esperada del cliente:

```
--> Pidiendo clave pública a nodo-01 (puerto 9991)...
--> Enviando tarea de prueba CIFRADA (RSA) a nodo-01 (puerto 9991)...
<-- Resultado recibido (cifrado=True): {'slope': 2.35, 'intercept': 0.81, 'mse': 0.04}
```

Y en la terminal de `nodo-01` se verá el recorrido completo:

```
[CRYPTO] Mensaje TASK_SUBMIT de cliente-prueba descifrado (RSA)
[EXECUTION] Recibida tarea de IA 'regresion_lineal' (task-101) enviada por cliente-prueba
[CRYPTO] Mensaje TASK_RESULT cifrado con RSA (8 bloques) -> puerto 9999
```

### 3. Comprobar que un mensaje sin cifrar se rechaza

```bash
python test_send_task.py --plano
```

El nodo responde en su log:

```
[CRYPTO] TASK_SUBMIT de cliente-prueba RECHAZADO: llegó sin cifrar
```

### 4. Elegir el algoritmo (RSA o ElGamal)

Se controla con la variable de entorno `CRYPTO_ALGO` (por defecto `rsa`). Debe definirse al iniciar cada nodo; cada nodo puede usar un algoritmo distinto, porque quien cifra usa el algoritmo indicado en la clave pública del destinatario.

```bash
# Linux / macOS
CRYPTO_ALGO=elgamal python run_node.py nodo-01 9991

# Windows (PowerShell)
$env:CRYPTO_ALGO="elgamal"; python run_node.py nodo-01 9991
```

Para que el cliente de prueba use el mismo algoritmo, defínela también al ejecutarlo.

### 5. Benchmark de generación de números

```bash
python benchmark_primos.py          # 100000 números por defecto
python benchmark_primos.py 5000     # cantidad personalizada
```

Genera números de 40 dígitos con 3 técnicas (`randint`, cadena de texto y LCG), evalúa su primalidad en paralelo con todos los núcleos y muestra cuántos primos aportó cada técnica.

### 6. Con Docker

```bash
docker-compose up --build
```

Levanta los 3 nodos (`nodo-01`, `nodo-02`, `nodo-03`) con `network_mode: host`, que funciona de forma nativa en Linux. Para usar ElGamal, agrega en cada servicio del `docker-compose.yml`:

```yaml
    environment:
      - CRYPTO_ALGO=elgamal
```

Luego ejecuta `python test_send_task.py` desde tu máquina.

---

## Cómo funciona

### Descubrimiento y tolerancia a fallos
- Cada nodo envía un **beacon** (`RESOURCE_BEACON`) cada 2 segundos a los demás con su CPU libre, RAM libre y su **clave pública**.
- Si un nodo pasa más de 5 segundos sin enviar beacons, se marca como `OFFLINE`; si vuelve, pasa a `ONLINE`.
- Si el nodo que ejecutaba una tarea se cae, el `TaskManager` la reasigna a otro nodo.

### Planificación
El `DistributedScheduler` filtra los nodos `ONLINE` que cumplan los requisitos de la tarea y elige el de mayor puntaje según la función de aptitud:

| Factor | Peso |
|---|---|
| CPU libre | 40 % |
| RAM libre | 40 % |
| Ancho de banda (simulado) | 10 % |
| Reputación (simulada) | 5 % |
| Latencia (simulada) | 5 % |

### Generación de primos
1. Se genera un candidato impar aleatorio de 40 dígitos con un generador criptográficamente seguro (`random.SystemRandom`).
2. Se descartan los múltiplos de primos pequeños.
3. Se verifica con **Miller-Rabin** (15 rondas, probabilidad de error despreciable).

### Criptosistemas

**RSA:** `N = p·q`, `e = 65537`, `d = e⁻¹ mod φ(N)`. Cifrar: `C = Mᵉ mod N`. Descifrar: `M = Cᵈ mod N`.

**ElGamal:** primo `p`, generador `g = 2`, clave privada `x`, pública `y = gˣ mod p`. Cifrar con `k` aleatorio por bloque: `C₁ = gᵏ mod p`, `C₂ = M·yᵏ mod p`. Descifrar: `M = C₂ · (C₁ˣ)⁻¹ mod p`.

**Cifrado por bloques:** el mensaje JSON se convierte a bytes y se parte en bloques que quepan en el módulo (31 bytes con RSA, 15 con ElGamal). Cada bloque lleva un byte marcador `0x01` al inicio para no perder ceros a la izquierda al convertir a entero.

### Tipos de mensaje

| Tipo | Cifrado | Descripción |
|---|---|---|
| `RESOURCE_BEACON` | No | Recursos del nodo + clave pública |
| `PUBKEY_REQUEST` / `PUBKEY_RESPONSE` | No | Handshake para que un cliente externo obtenga la clave pública de un nodo |
| `TASK_SUBMIT` | **Sí** | Envío de una tarea de IA |
| `TASK_RESULT` | **Sí** | Resultado de la tarea |
| `ENCRYPTED` | — | Sobre que envuelve a cualquier mensaje cifrado |

`MessageService` cifra y descifra de forma transparente: el resto del código recibe los mensajes ya descifrados con `header["secure"] = True`. Los mensajes que llegan en claro siempre se marcan con `secure = False`, así que no pueden hacerse pasar por seguros.

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

---

## Limitaciones conocidas

- Los beacons **no están firmados**: un atacante activo podría hacerse pasar por un nodo publicando su propia clave.
- RSA "de libro" sin relleno OAEP y ElGamal con `g = 2` sobre un primo no seguro; suficiente para fines académicos.
- Las llaves de 40 dígitos son vulnerables a factorización.
- La inferencia (`ai_worker.py`) es simulada: devuelve resultados fijos.
- Ancho de banda, reputación y latencia del scheduler están simulados con valor constante.
