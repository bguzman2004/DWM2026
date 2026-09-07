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
