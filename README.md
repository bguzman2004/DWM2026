Hola profesor, perdón por el desorden en github, pero esta todo, este va a ser el que voy a utilizar durante todo el semestre

## API GraphQL (Semana 5)

API de prueba para el menú del restaurante (modelo `Platillo`), con Node.js + Express + Apollo Server + Mongoose.

**Cómo levantarla:**
```bash
npm install
npm start          # nodemon server.js, escucha en http://localhost:8090/graphql
```
Requiere MongoDB corriendo en `mongodb://localhost:27017/dwm2026`.

**Operaciones disponibles:**
- `getPlatillos(limit, offset)` / `getPlatilloById(id)`
- `addPlatillo(input)` / `updPlatillo(id, input)` / `delPlatillo(id)`

**¿Por qué GraphQL y no gRPC acá?** Esta API la va a consumir el frontend de la web (el cliente pide justo los campos del platillo que necesita mostrar, sin más ni menos — eso es GraphQL). gRPC lo usaríamos si tuviéramos varios servicios internos hablando entre sí (por ejemplo, el servicio de pedidos consultando al servicio de inventario) y quisiéramos contratos tipados (`.proto`) y menor latencia — no es el caso de esta pantalla pensada para un solo cliente web.

## API Gateway con FastAPI (Semana 7)

Ejercicio de la clase del 16/09: dos APIs "backend" (una en inglés, otra en español) y un API Gateway que enruta según la URL a la que se llama. Está en `Semana 7/apigateway/`.

**Cómo levantarlo** (3 terminales, mismo entorno con `fastapi`, `uvicorn` y `httpx` instalados — `pip install -r "Semana 7/apigateway/requirements.txt"`):
```bash
# Terminal 1 — Backend API en inglés (puerto 9000)
cd "Semana 7/apigateway/fastapi"
uvicorn backend_api:app --host 0.0.0.0 --port 9000

# Terminal 2 — Backend API en español (puerto 9100)
cd "Semana 7/apigateway/fastapi2"
uvicorn backend_api:app --host 0.0.0.0 --port 9100

# Terminal 3 — API Gateway (puerto 8000)
cd "Semana 7/apigateway/gateway"
uvicorn gateway:app --host 0.0.0.0 --port 8000
```

**Probarlo:**
```bash
curl http://localhost:8000/api/products    # -> enruta al backend en inglés (9000)
curl http://localhost:8000/api/productos   # -> enruta al backend en español (9100)
curl http://localhost:8000/api/orders      # -> enruta al backend en inglés (9000)
curl http://localhost:8000/api/ordenes     # -> enruta al backend en español (9100)
```

`/api/ordenes` no se mostró en la clase en vivo (quedó como ejercicio) — se agregó acá siguiendo el mismo patrón que `/api/productos`, para que las 4 rutas del backend tengan su equivalente en el gateway.

## Backend seguro: autenticación, gateway y Vault (Semana 9)

Cuatro piezas, cada una con una sola responsabilidad:

| Pieza | Archivo | Puerto | Qué hace |
|---|---|---|---|
| Vault (modo desarrollo) | — | 8200 | Guarda los secretos |
| Authentication Service | `auth-service.py` | 8100 | Revisa usuario y contraseña (guardadas con hash), entrega un token de 15 minutos, dice si un token sigue vigente y cierra sesiones |
| API Gateway | `gateway.py` | 8000 | Única entrada: valida el token, revisa el rol y enruta al backend |
| Backend de menú | `backend_api.py` | 9000 | Entrega platillos y categorías, solo si la petición viene del gateway |

El gateway también enruta `/api/pedidos` y `/api/reservas` al puerto 9100; ese backend todavía no está en este repositorio.

**Cómo funciona:**
1. El usuario hace login en el gateway (`POST /auth/login`), que le pasa las credenciales al Authentication Service, y recibe un token.
2. Llama al gateway con `Authorization: Bearer <token>`.
3. El gateway le pregunta al Authentication Service si el token sigue vigente (con un secreto que saca de Vault) y revisa el rol.
4. Si todo está bien, llama al backend con un secreto interno y le avisa quién hizo la petición.

**Permisos:** ver (`GET`) lo puede hacer cualquier usuario con sesión; crear, editar o borrar (`POST`, `PUT`, `PATCH`, `DELETE`) solo el rol `admin`. Los usuarios de prueba están en `auth-service.py`.

**Levantarlo** (PowerShell, una terminal por servicio):
```powershell
# Authentication Service
$env:AUTH_INTROSPECTION_SECRET = "secreto-del-auth"
uvicorn auth-service:app --port 8100

# Backend de menú
$env:INTERNAL_GATEWAY_SECRET = "secreto-del-backend"
uvicorn backend_api:app --port 9000

# API Gateway
$env:VAULT_ADDR = "http://127.0.0.1:8200"
$env:VAULT_TOKEN = "token-de-vault"
uvicorn gateway:app --port 8000
```

Los secretos guardados en Vault tienen que ser los mismos que las variables de arriba: `auth_introspection_secret` igual a `AUTH_INTROSPECTION_SECRET`, y `backend_shared_secret` igual a `INTERNAL_GATEWAY_SECRET`:
```bash
vault kv put secret/gateway auth_introspection_secret="secreto-del-auth" backend_shared_secret="secreto-del-backend"
```
Cada servicio se niega a arrancar si le falta su secreto o su token.

**Probarlo con Postman:**
1. `POST http://127.0.0.1:8000/auth/login` con el body JSON `{"username": "...", "password": "..."}`. Devuelve un `access_token`.
2. `GET http://127.0.0.1:8000/api/platillos` con el header `Authorization: Bearer <access_token>`. Devuelve los platillos y quién hizo la petición (`identity`).
3. `POST http://127.0.0.1:8000/api/platillos` con el token de un usuario que no es admin: responde 403.
4. `POST http://127.0.0.1:8000/auth/logout` con el mismo header `Authorization`: cierra la sesión y el token deja de servir.

**Códigos que devuelve el gateway:** 401 sin token o con token vencido, 403 sin permiso para esa operación, 400 si la ruta no es válida, 502 si un servicio no responde, 500 si falla Vault o los secretos no coinciden, 429 si se hacen demasiados intentos fallidos de login.

### Authentication Service (Semana 10)

`auth-service.py` autentica al usuario y administra su sesión. No hace lógica de negocio ni enruta nada.

| Endpoint | Qué hace |
|---|---|
| `POST /login` | Valida usuario y contraseña y entrega un token de 15 minutos |
| `POST /introspect` | Dice si un token sigue activo y devuelve identidad, roles y vencimiento |
| `POST /logout` | Cierra la sesión (el token deja de servir) |
| `GET /health` | Estado del servicio |

- **Solo el gateway puede llamarlo:** los 4 endpoints exigen el header `X-Gateway-Auth-Secret`. Sin él (o con uno distinto) responde 403. Por eso el login y el logout de los usuarios pasan por el gateway (`/auth/login` y `/auth/logout`), que agrega el secreto sacándolo de Vault.
- **Contraseñas con hash:** `USERS` guarda `password_hash` (PBKDF2-HMAC-SHA256 con sal y 600.000 iteraciones), no la contraseña. Para agregar un usuario ejecuta `python auth_passwords.py`, escribe la contraseña y pega el resultado en `USERS`.
- **Mismo mensaje para usuario o contraseña incorrectos** (`Credenciales incorrectas`), y siempre se verifica un hash, exista el usuario o no: no se puede descubrir qué usuarios existen ni por el mensaje ni por el tiempo de respuesta.
- **Límite de intentos:** 5 intentos fallidos en 5 minutos bloquean a ese usuario por 60 segundos (responde 429 con `Retry-After`).
- **Sesiones:** viven en memoria (se pierden al reiniciar el servicio) y las vencidas se limpian en cada login.

### Pruebas automáticas

```bash
pip install -r requirements.txt
pytest -q
```

`test_auth_service.py` prueba el Authentication Service: el secreto en cada endpoint, el login, el vencimiento y el cierre de sesión de los tokens, el límite de intentos y que no haya contraseñas en texto plano.

## Mensajería asíncrona con STOMP (Semana 11)

Cuando un cliente hace un pedido, no conviene que el sistema se quede esperando a que la cocina lo procese. El pedido se deja en una **cola** y la cocina lo retira cuando puede. Quien envía (el **productor**) y quien recibe (el **consumidor**) no se conocen y no tienen que estar andando al mismo tiempo: el **broker** guarda los mensajes entre medio.

```
 productor.py ──STOMP──▶  broker (ActiveMQ)  ──STOMP──▶  consumidor.py
 arma el pedido           cola /queue/mariachi.pedidos    la cocina: revisa el pedido,
                          puerto 61613                    imprime la comanda y responde ACK o NACK
```

STOMP es un protocolo de texto simple para hablar con el broker. En Python se usa con la librería `stomp.py`.

| Archivo | Qué hace |
|---|---|
| `productor.py` | Arma un pedido (texto, ancho fijo, XML o JSON) y lo deja en la cola |
| `consumidor.py` | La cocina: saca los mensajes, los interpreta, imprime la comanda y los confirma (ACK) o rechaza (NACK) |
| `contrato.py` | El menú, el 2x1 y el formato de cada mensaje. Lo usan los dos programas |
| `broker_prueba.py` | Broker STOMP mínimo para probar sin instalar ActiveMQ |
| `test_stomp.py` | Pruebas automáticas |

### El pedido

Un pedido tiene un número de orden (`id`, de 1 a 6 dígitos), el `cliente`, la lista de `items` (platillo y cantidad) y el `monto`. Los platillos salen del menú:

| N° | Platillo | Precio |
|---|---|---|
| 1 | Tacos al Pastor | $2.500 (promo 2x1) |
| 2 | Burrito Especial | $4.500 |
| 3 | Nachos Supreme | $3.500 |
| 4 | Quesadilla Mixta | $3.200 |

Un pedido lleva de 1 a 9 platillos distintos y de 1 a 20 unidades de cada uno. En el 2x1 se pagan la mitad de las unidades, redondeando hacia arriba (3 tacos se pagan como 2). El productor calcula el `monto` con el menú y el consumidor lo vuelve a calcular: **si el total no coincide, rechaza el pedido**.

### Formatos de mensaje

El mismo pedido puede viajar de cuatro formas. El productor avisa cuál usó en los headers `x-formato` y `content-type`; si faltan, el consumidor trata el mensaje como texto.

| `--formato` | `content-type` | Cómo viaja |
|---|---|---|
| `texto` | `text/plain` | Texto libre. Es un aviso, no un pedido |
| `fijo` | `text/plain` | Registro de ancho fijo (ver abajo) |
| `xml` | `application/xml` | `<pedido>` con `<id>`, `<cliente>`, `<monto>` y `<items>` |
| `json` | `application/json` | Objeto con `id`, `cliente`, `items` y `monto` |

El pedido `482913` de Camila Rojas (2 tacos y 1 quesadilla, total $5.700) en cada formato:

```
482913Camila Rojas        0005700.00201020401
<pedido><id>482913</id><cliente>Camila Rojas</cliente><monto>5700.00</monto><items><item><platillo>1</platillo><cantidad>2</cantidad></item><item><platillo>4</platillo><cantidad>1</cantidad></item></items></pedido>
{"id": "482913", "cliente": "Camila Rojas", "items": [{"platillo": 1, "cantidad": 2}, {"platillo": 4, "cantidad": 1}], "monto": "5700.00"}
```

**Ancho fijo:** cada dato ocupa un lugar exacto dentro del texto.

| Posiciones | Dato | Relleno |
|---|---|---|
| 1 a 6 | `id` | ceros a la izquierda |
| 7 a 26 | `cliente` (hasta 20 caracteres) | espacios a la derecha |
| 27 a 36 | `monto` | ceros a la izquierda, con punto y 2 decimales |
| 37 | cantidad de items (1 a 9) | |
| 38 en adelante | por cada item: platillo (2) y cantidad (2) | ceros a la izquierda |

Como el registro solo admite ASCII, las tildes y la ñ se pasan a letras sin tilde (`Matías Cañete` queda `Matias Canete`). En JSON y XML se conservan.

### Cómo probarlo

**1. Broker.** Con ActiveMQ (lo que se vio en clase): descargar ActiveMQ Classic desde activemq.apache.org, descomprimirlo y, desde su carpeta `bin`, ejecutar `activemq start`. Necesita Java instalado (revisa qué versión pide la que descargues). Abre, entre otros, el puerto `61613` de STOMP, y la cola se crea sola con el primer mensaje. Para probar rápido sin instalar nada, este repositorio trae un broker mínimo que habla el mismo protocolo:

```bash
python broker_prueba.py
```

**2. Librería y clave.** La clave del broker no está en el código: va en la variable `STOMP_CLAVE` (o en `--clave`).

```bash
pip install -r requirements.txt
$env:STOMP_CLAVE = "demo123"     # PowerShell   (en CMD: set STOMP_CLAVE=demo123)
```

**3. Consumidor** (una terminal) y **productor** (otra terminal):

```bash
python consumidor.py

python productor.py --formato texto --mensaje "Mesa 4 pide la cuenta"
python productor.py --formato fijo --id 482913 --cliente "Camila Rojas" --item 1:2 --item 4:1
python productor.py --formato xml  --id 482913 --cliente "Camila Rojas" --item 1:2 --item 4:1
python productor.py --formato json --id 77 --cliente "Matías Cañete" --item 2:1 --item 3:2 --item 1:3
python productor.py --formato json --id 78 --monto 100
```

Cada comando muestra lo que envió, por ejemplo:

```
Mensaje enviado a /queue/mariachi.pedidos (formato=fijo):
482913Camila Rojas        0005700.00201020401
```

Y la cocina imprime:

```
Cocina escuchando /queue/mariachi.pedidos. Presiona Ctrl+C para salir.

[AVISO] formato=texto
Mesa 4 pide la cuenta

[COMANDA] pedido MRC-482913 · Camila Rojas · formato=fijo
  2 x Tacos al Pastor (2x1)
  1 x Quesadilla Mixta
  Total: $5.700

[COMANDA] pedido MRC-000077 · Matías Cañete · formato=json
  1 x Burrito Especial
  2 x Nachos Supreme
  3 x Tacos al Pastor (2x1)
  Total: $16.500

[MENSAJE NO VALIDO] Monto $100 no coincide con el menu: el total es $5.700
```

| Opción | Programa | Para qué |
|---|---|---|
| `--formato` | productor | `texto`, `fijo`, `xml` o `json` |
| `--id`, `--cliente` | productor | número de orden y nombre del cliente |
| `--item PLATILLO:CANTIDAD` | productor | un platillo del pedido (se puede repetir). Sin `--item` envía 2 tacos y 1 quesadilla |
| `--monto` | productor | por defecto se calcula con el menú; sirve para probar un total alterado |
| `--mensaje` | productor | el texto, con `--formato texto` |
| `--host`, `--port`, `--usuario`, `--clave` | ambos | dónde está el broker (por defecto `127.0.0.1:61613`) y cómo entrar |
| `--max-mensajes N` | consumidor | termina después de atender N mensajes |
| `--espera S` | consumidor | termina si pasan S segundos sin mensajes |

### ACK y NACK

El consumidor se suscribe con `ack="client-individual"` y `prefetch-count=1`: el broker entrega **un mensaje a la vez** y espera la respuesta antes de mandar el siguiente.

| Situación | Respuesta | Resultado |
|---|---|---|
| El pedido se leyó bien y el total coincide con el menú | `ack` | sale de la cola y se imprime la comanda |
| El mensaje está mal armado o el total no coincide | `nack` con `requeue:false` | no se reintenta: reintentar un mensaje malo no lo arregla |

Qué hace el broker con un `nack` depende del broker (en ActiveMQ normalmente queda en su cola de mensajes muertos para revisarlo). Si el consumidor se cae sin responder, el mensaje no se pierde: el broker lo vuelve a entregar.

### Qué se mejoró sobre la primera versión

El formato de los mensajes no cambió: se comparó con la primera versión en 1.200 pedidos y los mensajes son idénticos.

- **Un solo contrato.** El menú, el 2x1, el cálculo del total y los cuatro formatos estaban copiados en el productor y en el consumidor; ahora viven en `contrato.py`.
- **Validaciones en los dos extremos.** El `id` debe tener de 1 a 6 dígitos en todos los formatos (antes solo en ancho fijo), el `cliente` no puede ir vacío ni traer saltos de línea o códigos de control (antes un nombre con un código de escape llegaba tal cual a la comanda), y el `monto` debe ser un número entre 0 y 9999999.99 con hasta 2 decimales en todos los formatos (antes el productor armaba mensajes con montos negativos o de 3 decimales).
- **Lectura más estricta.** Un platillo o una cantidad decimal ya no se trunca en silencio (`1.9` se leía como `1`), el XML con `DOCTYPE` o `ENTITY` se rechaza, y el registro de ancho fijo solo admite ASCII.
- **Errores que se entienden.** Un JSON sin `items` decía solo `'items'`; ahora dice qué campos faltan.
- **Tildes y ñ** en ancho fijo en vez de un error.
- **El ACK ya no se confunde con un mensaje inválido:** se responde fuera del bloque que revisa el mensaje.
- **Sin broker.** El productor y el consumidor avisan si no encuentran el broker (código de salida 1) en vez de terminar con un traceback.
- **`--espera`** en el consumidor y el número de orden siempre con 6 dígitos en la comanda (`MRC-000077`).

### Pruebas automáticas

```bash
pip install -r requirements.txt
pytest -q
```

`test_stomp.py` no necesita ActiveMQ y tiene dos partes:

- **El contrato:** el total con el menú y el 2x1, cada formato armado y leído de vuelta, las tildes, el escape de caracteres especiales en XML y una lista larga de mensajes mal armados que deben rechazarse.
- **El recorrido completo:** el productor y el consumidor reales conversan a través de `broker_prueba.py`. Se prueba que cada formato llega y se imprime bien, que un total alterado se rechaza, que los mensajes llegan de a uno y en orden, que un mensaje inválido se rechaza y la cola sigue, que un mensaje sin confirmar vuelve a la cola, y que los programas avisan cuando falta la clave o el broker.

`pytest -q` corre también las pruebas del Authentication Service (`test_auth_service.py`).

### Limitaciones

- `broker_prueba.py` no es ActiveMQ: vive en memoria, no guarda nada en disco y acepta cualquier usuario. Sirve para probar, no para producción.
- Por ahora la cocina solo imprime la comanda. El siguiente paso es que el consumidor entregue los pedidos al backend a través del gateway.
