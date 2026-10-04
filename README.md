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
| Authentication Service | `auth-service.py` | 8100 | Revisa usuario y contraseña, entrega un token de 15 minutos y dice si un token sigue vigente |
| API Gateway | `gateway.py` | 8000 | Única entrada: valida el token, revisa el rol y enruta al backend |
| Backend de menú | `backend_api.py` | 9000 | Entrega platillos y categorías, solo si la petición viene del gateway |

El gateway también enruta `/api/pedidos` y `/api/reservas` al puerto 9100; ese backend todavía no está en este repositorio.

**Cómo funciona:**
1. El usuario hace login en el Authentication Service y recibe un token.
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
1. `POST http://127.0.0.1:8100/login` con el header `X-Gateway-Auth-Secret` (el secreto del auth) y el body JSON `{"username": "...", "password": "..."}`. Devuelve un `access_token`.
2. `GET http://127.0.0.1:8000/api/platillos` con el header `Authorization: Bearer <access_token>`. Devuelve los platillos y quién hizo la petición (`identity`).
3. `POST http://127.0.0.1:8000/api/platillos` con el token de un usuario que no es admin: responde 403.

**Códigos que devuelve el gateway:** 401 sin token o con token vencido, 403 sin permiso para esa operación, 400 si la ruta no es válida, 502 si un servicio no responde, 500 si falla Vault o los secretos no coinciden.
