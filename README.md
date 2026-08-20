# Chat multicliente sobre sockets TCP

Servidor de chat que atiende múltiples clientes en simultáneo con un solo hilo, usando multiplexación de E/S con `select()`. Incluye cliente de terminal con reconexión automática.

**Stack:** Python 3 — solo librería estándar (`socket`, `select`, `threading`, `time`). Sin dependencias externas.

> **Nota sobre el nombre:** el repo se llama `WebSocket` pero el proyecto usa **sockets TCP crudos** (API de Berkeley), no el protocolo WebSocket (RFC 6455). No hay handshake HTTP ni framing: son bytes directos sobre TCP.

---

## Cómo correrlo

Necesitás dos o más terminales.

```bash
# Terminal 1 — servidor
python server.py

# Terminal 2, 3, 4... — un cliente por terminal
python client.py
```

El cliente pide un username al arrancar y después todo lo que escribas se difunde al resto. Se corta con `Ctrl+C`.

Por defecto: `127.0.0.1:6869`, buffer de 1024 bytes.

---

## Qué hace

**Servidor (`server.py`)**

- Un único hilo atiende a todos los clientes. `select()` bloquea hasta que algún socket tiene datos listos y devuelve solo esos; el loop recorre los sockets listos y decide: si es el socket del servidor, hay una conexión nueva por aceptar; si es un cliente, hay un mensaje por difundir.
- Broadcast a todos los conectados menos el remitente.
- Los sockets se ponen en modo no bloqueante (`setblocking(False)`), así una lectura sin datos lanza excepción en lugar de congelar el loop entero.
- `SO_REUSEADDR` evita el "Address already in use" del estado TIME_WAIT al reiniciar el servidor.
- Desconexión limpia: un `recv()` que devuelve vacío significa que el cliente cerró, y el socket se saca de la lista y se cierra. Un `send()` fallido durante el broadcast también desconecta a ese cliente.
- `Ctrl+C` cierra todos los sockets en el bloque `finally`.

**Cliente (`client.py`)**

- Dos hilos, porque `input()` es bloqueante: el hilo principal lee del teclado y envía; un hilo secundario recibe y muestra los mensajes ajenos. Sin esa separación, el cliente no podría mostrar nada mientras espera que escribas.
- El hilo receptor es `daemon=True`, así muere junto al principal y no deja el proceso colgado.
- Reconexión automática: si el servidor no está levantado o se cae, el cliente reintenta cada 3 segundos en lugar de abortar.
- Cierre coordinado con una bandera global `closing`, que ambos hilos consultan para distinguir un cierre intencional de un error real de red.

---

## Estructura

```
server.py              Servidor multicliente con select() + broadcast
client.py              Cliente con hilo receptor y reconexión automática
Ejercicio/
├── server.py          Versión mínima: un solo cliente, sin manejo de errores
├── cliente.py         Su contraparte
└── tarea.ipynb        Notebook con la teoría estudiada antes de codear
```

`Ejercicio/` es el punto de partida del challenge: la versión más simple posible, un servidor que acepta un cliente y recibe mensajes. Los archivos de la raíz son la evolución a multicliente.

---

## Decisiones de diseño

**`select()` en lugar de un hilo por cliente.** El modelo thread-per-client es más fácil de escribir pero escala mal: cada conexión cuesta un hilo del sistema operativo y aparecen condiciones de carrera sobre la lista de clientes. Con `select()` todo pasa en un solo hilo, la lista de sockets no necesita locks, y el costo por cliente es un descriptor de archivo.

**El socket del servidor va en la misma lista que los clientes.** `SOCKETS` contiene tanto el socket que escucha como los conectados. Para `select()` un "cliente listo para leer" y un "servidor con conexión pendiente" son el mismo evento de lectura: solo cambia qué se hace con él. Eso evita tener dos listas y dos llamadas a `select()`.

**El servidor no decodifica para reenviar.** El broadcast reenvía los bytes tal como llegaron. El `decode('utf-8')` se hace solo para el log de consola y va envuelto en su propio `try`, así un mensaje mal codificado ensucia el log pero no rompe la difusión ni tumba al servidor.

**El broadcast itera sobre una copia de la lista de sockets.** Si durante la difusión el `sendall()` a un cliente falla, ese cliente se desconecta — y desconectarlo lo saca de `SOCKETS`. Mutar una lista mientras se la recorre hace que Python **saltee el elemento siguiente**: el cliente que venía después del muerto se quedaba sin recibir el mensaje, en silencio y sin error. Recorrer `list(SOCKETS)` desacopla la iteración de las bajas.

**`sendall()` y no `send()`.** `send()` puede escribir menos bytes de los pedidos y devolver cuántos escribió; si nadie mira ese número, el mensaje llega truncado del otro lado. `sendall()` insiste hasta colocar el buffer completo. Con mensajes cortos la diferencia no se nota, pero es una truncación silenciosa esperando volumen.

**El cliente publica el socket recién cuando `connect()` salió bien.** La conexión se arma sobre una variable local y solo después se asigna a la global. Si se asignara antes, el hilo principal vería un socket "listo" y le haría `sendall()` mientras todavía se está conectando. En el mismo camino, un intento fallido se cierra explícitamente: sin eso, cada reintento cada 3 segundos filtraba un descriptor de archivo durante toda la caída.

**El username lo arma el cliente.** El formato `usuario: mensaje` se compone del lado del cliente antes de enviar. Simplifica el servidor —que solo mueve bytes— a costa de que el nombre no esté verificado: cualquier cliente puede declarar el que quiera.

---

## Contexto

Challenge de fundamentos de redes. La consigna original pedía "un socket servidor y cliente lo más básico posible para un cliente, sin manejo de errores" — eso es lo que está en `Ejercicio/`.

El notebook `Ejercicio/tarea.ipynb` documenta el estudio previo: sockets de Berkeley y API BSD, el stack de protocolos de Internet y sus cuatro capas de abstracción, su relación con el modelo OSI, TCP y su handshake de tres vías, UDP y checksum, multiplexación y concurrencia, agotamiento de IPv4, y una pasada por TLS/SSL. La teoría se estudió antes de escribir la primera línea, con documentación oficial de Python y Wikipedia.

La versión multicliente de la raíz es la extensión posterior a la consigna mínima.

---

## Limitaciones conocidas

- **Sin framing de mensajes.** TCP es un flujo de bytes, no de mensajes: dos envíos rápidos pueden llegar juntos en un solo `recv()`, y un mensaje largo puede llegar partido. Un protocolo real prefijaría la longitud o usaría un delimitador. Con mensajes cortos de chat el problema casi no aparece, pero está.
- **Sin autenticación.** El username es declarativo; cualquiera puede suplantar a otro.
- **Sin cifrado.** Todo viaja en texto plano. Sirve para localhost, no para una red abierta.
- **`recv(1024)` puede truncar.** Mensajes de más de 1024 bytes se cortan.
