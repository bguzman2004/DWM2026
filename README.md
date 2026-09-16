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
