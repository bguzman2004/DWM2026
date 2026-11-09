import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common.topology import EDGES, edge_path
from services.api_gateway.routes import ROUTES

EV = {r["id"]: r for r in json.loads((ROOT / "docs/evidencia/ejecuciones.json").read_text())}
BENCH = json.loads((ROOT / "bench/results.json").read_text())
junit = ET.parse(ROOT / "docs/evidencia/pytest.xml").getroot()
suite = junit if junit.tag == "testsuite" else junit[0]
RESULT = {}
for case in suite.iter("testcase"):
    bad = case.find("failure") is not None or case.find("error") is not None
    RESULT[case.get("name").split("[")[0]] = RESULT.get(case.get("name").split("[")[0], True) and not bad
TOTAL = int(suite.get("tests"))
TIME = float(suite.get("time"))
FALLAS = int(suite.get("failures", 0)) + int(suite.get("errors", 0))
MUT = json.loads((ROOT / "docs/evidencia/mutaciones.json").read_text())
SMOKE = (ROOT / "docs/evidencia/smoke_e2e.txt").read_text().strip().splitlines()


def cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def tabla(headers, rows):
    largos = []
    for i, h in enumerate(headers):
        valores = [len(str(r[i])) for r in rows] or [0]
        promedio = sum(valores) / len(valores)
        largos.append(int(min(max(promedio, len(h) + 2, 10), 90)))
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("-" * n for n in largos) + "|"]
    for row in rows:
        out.append("| " + " | ".join(cell(c) for c in row) + " |")
    return "\n".join(out) + "\n"


def jbloque(obj, limite=1400):
    texto = json.dumps(obj, indent=2, ensure_ascii=False)
    if len(texto) > limite:
        texto = texto[:limite] + "\n  ..."
    return "```json\n" + texto + "\n```\n"


def prueba(*nombres):
    marcas = []
    for n in nombres:
        marcas.append(f"`{n}` " + ("✔" if RESULT.get(n) else "✘ (no encontrada o falla)"))
    return "; ".join(marcas)


def ev(clave, campo="respuesta"):
    return EV[clave][campo]


md = []
w = md.append

w("""---
title: "Evaluación de la Unidad 2 — Backend seguro completo"
subtitle: "Caso El Mariachi (restaurante de comida mexicana)"
lang: es
---
""")

w("# Portada\n")
w(tabla(["Campo", "Detalle"], [
    ["Asignatura", "Desarrollo Web y Móvil (DWM2026)"],
    ["Evaluación", "Unidad 2 — Diseño e implementación de un backend seguro completo (entrega 09-nov-2026)"],
    ["Caso de negocio", "El Mariachi: restaurante de comida mexicana (tacos, burritos, nachos y otros). **Número en el listado de 40 casos: por completar por el equipo antes de entregar.**"],
    ["Integrantes", "Benjamín Guzmán (GitHub bguzman2004) y Matías Cañete"],
    ["Versión del frontend", "Frontend responsivo de la Evaluación 1 (index.html, script.js, style.css e imágenes), entregado junto a este backend en la carpeta `evaluacion1_frontend`. Vistas: Inicio (con Pedido Rápido por WhatsApp), Menú, Detalle de platillo, Pedido, Confirmación, Nosotros y Contacto. Menú de 12 platillos en 5 categorías (Tacos, Burritos, Nachos, Bebidas, Otros)"],
    ["Alcance de integración", "Instrucción del docente, confirmada al equipo en la clase del 02-11-2026: «La evaluación, son datos de frontend, no es que hay que integrar el frontend […] yo solamente pedí en la evaluación 2 que tuvieran cómo probarlo». Por eso las pantallas no se conectan; el módulo 10.4 ejecuta los servicios con **los mismos datos del frontend** (platillos, promoción, formulario y carrito de `script.js`) a través del API Gateway, y las pruebas automatizadas los repiten."],
    ["Código fuente", "Carpeta `mariachi_backend/` (Python 3.12/3.13, FastAPI, Strawberry GraphQL, gRPC, SQLite, HashiCorp Vault)"],
    ["Resultado de pruebas", f"{TOTAL} pruebas automatizadas, {FALLAS} fallas, en {TIME:.0f} s (evidencia: `docs/evidencia/pytest.xml`)"],
]))
w("""
## Requisitos del caso y brechas declaradas

Los requisitos se derivan de las vistas del frontend y de las exigencias de la guía. Un requisito sin pantalla se registra como brecha de interfaz: el servicio existe y está probado, falta la pantalla que lo use.

""")
w(tabla(["ID", "Requisito", "Pantalla", "Estado"], [
    ["R01", "Ver la carta y la promoción del día sin identificarse", "P01 Inicio, P02 Menú", "Backend: S04/S05 y S34 públicos; el 2x1 lo calcula el servidor (brecha B1 resuelta)"],
    ["R02", "Buscar y filtrar el menú por categoría (Tacos, Burritos, Nachos, Bebidas, Otros) y ver el detalle de un platillo", "P02 Menú, P02b Detalle", "Backend: S04 con filtro `category` y S05 para el detalle. Búsqueda por texto: se resuelve en el navegador sobre la lista cargada"],
    ["R03", "Armar el pedido (carrito) y confirmarlo con notas de hasta 200 caracteres", "P03 Pedido", "Backend: S15 (total y precios calculados en el servidor). El carrito vive solo en el navegador"],
    ["R04", "Datos de contacto (nombre, teléfono, correo) del cliente", "P03 Pedido", "Backend: perfil en `clients` (S12/S14). El servidor repite las reglas del formulario: nombre ≥ 3 caracteres y celular chileno (`9XXXXXXXX`, se guarda como `+569XXXXXXXX`)"],
    ["R05", "Ver la confirmación con número, fecha, cliente, ítems y total", "P04 Confirmación", "Backend: consulta GraphQL `order(id)` (S30)"],
    ["R06", "Pagar el pedido", "— (brecha B2)", "Backend: S22/S23/S24 con proveedor simulado"],
    ["R07", "Registro e ingreso de clientes", "— (brecha B2)", "Backend: S01/S02/S03/S33"],
    ["R08", "Historial de pedidos propios", "— (brecha B2)", "Backend: S16/S17 y GraphQL `myOrders`"],
    ["R09", "Cocina prepara pedidos pagados", "— (brecha B2)", "Backend: S16/S19 con control de transición"],
    ["R10", "Administración gestiona carta y stock", "— (brecha B2)", "Backend: S06–S10"],
    ["R11", "Resumen de ventas para el dueño", "— (brecha B2)", "Backend: analítica S27–S29 y GraphQL `salesSummary`"],
    ["R12", "Información institucional y de contacto", "P05 Nosotros, P05b Contacto", "Contenido estático: no requiere servicio. El Pedido Rápido de Inicio abre WhatsApp y no pasa por el backend"],
]))
w("""
| Brecha | Descripción | Resolución propuesta |
|---|---|---|
| B1 | **Resuelta.** La promoción «2x1 en Tacos al Pastor» era solo texto del frontend. | Entidad `Promocion` en `inventory` (S34 consulta pública, S35 activar/desactivar por admin). El descuento se calcula al reservar stock y `orders` guarda subtotal, descuento y total; el navegador no puede enviarlo (prueba `test_p01_promocion_del_dia_se_aplica_en_el_servidor`). |
| B2 | No existen pantallas de ingreso/registro, pago, historial, cocina ni administración. | Pantallas P06–P10 a cargo del frontend cuando se integre; los servicios y sus contratos ya están implementados y probados. Según la instrucción docente, en esta entrega no se integra el frontend. |
| B3 | El frontend genera localmente el número de orden (`MRC-######`) y calcula su propio total (ya aplica el 2x1 con la misma regla que el servidor). | Al integrar: reemplazar `generarNumeroOrden()` por el `id` de S15 y mostrar el `subtotal`, `discount` y `total` que devuelve el servidor, que es el oficial. |
| B4 | Despacho, boletas y mensajería. | **Despacho no aplica:** el formulario P03 no captura dirección, el pedido es para retiro o consumo en el local. **Boletas y mensajería:** no aparecen en las pantallas; la boleta electrónica la emitiría un proveedor externo autorizado y los enlaces de Instagram/WhatsApp y el Pedido Rápido abren servicios externos sin pasar por el backend. Se declaran fuera de alcance. |

""")

w("""# Módulo 1 — Servicios derivados del frontend

## 1.1 Trazabilidad de pantallas

""")
w(tabla(["Pantalla", "Acciones en el frontend", "Servicios"], [
    ["P01 Inicio", "Ver banner, promoción del día y botón «Ver Menú»", "S34"],
    ["P02 Menú", "Cargar platillos, buscar, filtrar por categoría, agregar al carrito", "S04"],
    ["P02b Detalle de platillo", "Ver descripción, precio, promoción y elegir cantidad", "S05, S34"],
    ["P03 Pedido", "Ver carrito, completar contacto y notas, confirmar", "S15 (y S02 si no hay sesión, S12/S14 para el perfil)"],
    ["P04 Confirmación", "Mostrar número, fecha, cliente, teléfono, ítems y total", "S30 (`order`) o S17 + S12"],
    ["P05 Nosotros", "Texto institucional", "—"],
    ["P05b Contacto", "Dirección, horario, mapa y WhatsApp", "— (contenido estático)"],
    ["P06 Ingreso/Registro (brecha)", "Crear cuenta, iniciar y cerrar sesión", "S01, S02, S03, S33"],
    ["P07 Mis pedidos (brecha)", "Listar y consultar pedidos propios, anular", "S16, S17, S18, S30"],
    ["P08 Pago (brecha)", "Iniciar pago y ver su resultado", "S22, S24"],
    ["P09 Cocina (brecha)", "Ver pedidos pagados y avanzarlos", "S16, S19"],
    ["P10 Administración (brecha)", "Carta, stock, promociones, clientes, conciliaciones, ventas", "S06–S11, S13, S20, S21, S26, S32, S35"],
]))
w("""
Una variación visual entre escritorio y móvil no genera servicios nuevos: ambas versiones usan los mismos contratos.

## 1.2 Catálogo de servicios

Todos los servicios externos pasan por el API Gateway (`/…`). La numeración S01–S35 se mantiene en todo el informe (S33–S35 se agregaron después de S32 para no renumerar). PUT no se utiliza: ningún recurso se reemplaza completo; las modificaciones son parciales y se expresan con PATCH (semántica: se actualizan solo los campos enviados). DELETE sobre productos es una baja lógica para conservar el historial de pedidos.

""")
S = [
    ["S01", "R07", "P06 · registrarse", "Crear cuenta de cliente y su perfil", "POST /auth/register", "username (3–32, `[a-z0-9_]`), password (8–128), name (3–80), email, phone? (celular chileno)", "201 {user_id, client_id, username}", "409 usuario o correo repetido; 422 datos inválidos; 429 límite de tasa. Rol siempre `customer`", "password: credencial; email/phone: restringido", "Anónimo"],
    ["S02", "R07", "P06 · ingresar", "Iniciar sesión", "POST /auth/login", "username, password", "200 {user, expires_in} + cookie `session_token` HttpOnly", "401 mismo mensaje para usuario inexistente o clave errónea; 429 bloqueo tras 5 fallos o límite de tasa", "credencial", "Anónimo"],
    ["S03", "R07", "P06 · salir", "Cerrar y revocar la sesión", "POST /auth/logout", "cookie", "200 {revoked}", "503 si no se pudo revocar", "—", "Autenticado"],
    ["S33", "R07", "P06", "Identidad de la sesión actual", "GET /auth/me", "cookie", "200 {user_id, username, roles, client_id}", "401", "restringido", "Autenticado"],
    ["S04", "R01, R02", "P02 · cargar platillos", "Consultar catálogo", "GET /products?category&limit&offset", "category ∈ {Tacos, Burritos, Nachos, Bebidas, Otros}?, limit 1–100, offset ≥ 0", "200 {items:[{id,name,category,price,active,in_stock}], total}", "422 filtro inválido. Solo campos públicos; cocina/admin ven además on_hand, reserved, available. Los ids 1–12 son los platillos del frontend", "público", "Anónimo (identidad opcional)"],
    ["S34", "R01", "P01 · banner de promoción", "Consultar promociones vigentes", "GET /promotions", "—", "200 {items:[{id, product_id, product_name, kind:\"2x1\", label, active}]}", "Solo vigentes y de productos activos; admin ve también las inactivas", "público", "Anónimo (identidad opcional)"],
    ["S35", "R10", "P10 · promoción del día", "Activar o desactivar una promoción", "PATCH /promotions/{id}", "active: boolean", "200 promoción", "404; 403 sin rol admin. Afecta solo pedidos nuevos: los creados conservan su descuento", "interno", "admin"],
    ["S05", "R01", "P02", "Obtener un producto", "GET /products/{id}", "id", "200 producto", "404 si no existe o está inactivo", "público", "Anónimo"],
    ["S06", "R10", "P10 · agregar platillo", "Crear producto con stock inicial", "POST /products", "name, category, price > 0, stock ≥ 0", "201 producto", "409 nombre repetido; 403 sin rol admin", "interno", "admin"],
    ["S07", "R10", "P10 · editar platillo", "Modificar nombre, precio o estado", "PATCH /products/{id}", "name?, price?, active?", "200 producto", "404; 409; 422 sin cambios", "interno", "admin"],
    ["S08", "R10", "P10 · quitar platillo", "Baja lógica", "DELETE /products/{id}", "id", "200 {deactivated}", "404. No borra filas: se conserva el historial", "interno", "admin"],
    ["S09", "R10, R09", "P09/P10 · ver stock", "Consultar existencias", "GET /stock", "—", "200 {items con on_hand, reserved, available}", "403 para clientes", "interno", "kitchen, admin"],
    ["S10", "R10", "P10 · ajustar stock", "Reponer o dar de baja unidades", "POST /stock/{id}/adjust", "delta, reason (3–120)", "200 producto", "409 si deja el stock bajo lo reservado o bajo cero", "interno", "kitchen, admin"],
    ["S11", "R10", "P10 · clientes", "Listar clientes", "GET /clients?limit&offset", "—", "200 {items, total}", "403 sin rol admin", "restringido", "admin"],
    ["S12", "R04, R05", "P03/P04 · contacto", "Obtener un cliente", "GET /clients/{id}", "id", "200 cliente (completo para dueño/admin; solo id y nombre para cocina)", "404 si no es el dueño ni personal", "restringido", "Autenticado"],
    ["S13", "R10", "P10", "Crear cliente (alta administrativa)", "POST /clients", "name, email, phone?", "201 cliente", "409 correo repetido", "restringido", "admin"],
    ["S14", "R04", "P03 · contacto", "Actualizar datos propios", "PATCH /clients/{id}", "name? (≥ 3), email?, phone? (`(+56)9XXXXXXXX`)", "200 cliente (teléfono normalizado a `+569XXXXXXXX`)", "422 nombre corto, teléfono o correo inválido; 404 si no es el dueño ni admin; 409 correo repetido", "restringido", "customer (propio), admin"],
    ["S15", "R03, R05", "P03 · confirmar pedido", "Crear pedido y reservar stock", "POST /orders (+ Idempotency-Key opcional)", "items:[{product_id, qty 1–20}] (1–20 líneas), notes ≤ 200", "201 pedido {id, status:pendiente_pago, subtotal, discount, total, items[{…, discount, promo}], notes}; 200 si la clave ya existía", "409 sin stock o producto no disponible; 422; 502/503 si una dependencia cae. **Precio, descuento 2x1, total y estado los calcula el servidor**; `total`, `unit_price`, `discount` o `status` enviados por el navegador se ignoran", "restringido (pedido)", "customer"],
    ["S16", "R08, R09", "P07/P09", "Listar pedidos", "GET /orders?status&limit&offset", "—", "200 {items, total}", "customer: solo propios; kitchen: pagado/preparando/listo; admin: todos", "restringido", "Autenticado"],
    ["S17", "R05, R08", "P04/P07", "Consultar un pedido", "GET /orders/{id}", "id", "200 pedido", "404 si es de otro cliente (no se revela su existencia)", "restringido", "Autenticado"],
    ["S18", "R08", "P07 · anular", "Anular pedido y liberar stock", "POST /orders/{id}/cancel", "—", "200 {status:cancelado, stock_released, refund_required}", "409 si ya está pagado (cliente) o avanzado; el registro se conserva", "restringido", "customer (propio, solo pendiente), admin"],
    ["S19", "R09", "P09 · avanzar", "Preparando → listo → entregado", "PATCH /orders/{id}/status", "status ∈ {preparando, listo, entregado}", "200 pedido", "409 transición inválida (p. ej. pendiente_pago → preparando); al pasar a preparando se confirma el stock", "interno", "kitchen, admin"],
    ["S20", "R10", "P10", "Expirar pedidos sin pago y recuperar stock", "POST /orders/expire-pending?older_than_seconds", "0–86400 (def. 900)", "200 {expired:[ids]}", "No toca pedidos pagados", "interno", "admin"],
    ["S21", "R10", "P10", "Reintentar liberaciones de stock pendientes", "POST /orders/reconcile-stock", "—", "200 {released, pending}", "Idempotente", "interno", "admin"],
    ["S22", "R06", "P08 · pagar", "Iniciar pago de un pedido propio", "POST /payments (Idempotency-Key obligatorio)", "order_id", "201 pago {id, amount, status:pending, provider_ref, reused}", "404 pedido ajeno; 409 pedido no pagable o clave usada con otra orden; monto siempre desde `orders`", "restringido", "customer"],
    ["S23", "R06", "(proveedor)", "Recibir la notificación del proveedor", "POST /payments/webhook", "cuerpo JSON firmado con HMAC-SHA256 en `X-Signature`: event_id, type, provider_ref, amount", "200 {status: processed|duplicate, payment_status, order_sync}", "401 firma inválida; 409 monto distinto; 404 referencia desconocida; duplicado = 200 sin efectos", "secreto de integración", "Anónimo + firma"],
    ["S24", "R06", "P08", "Consultar un pago", "GET /payments/{id}", "id", "200 pago", "404 si no es del cliente", "restringido", "customer, admin"],
    ["S25", "R06", "P08", "Listar pagos", "GET /payments?order_id", "—", "200 {items}", "customer: solo propios", "restringido", "customer, admin"],
    ["S26", "R10", "P10", "Conciliar pagos cuyo aviso a `orders` falló", "POST /payments/reconcile", "—", "200 {results}", "Idempotente", "interno", "admin"],
    ["S27", "R11", "P10", "Sincronizar hechos de venta (gRPC `Sync`)", "interno · vía mutación `syncAnalytics`", "—", "imported", "Idempotente (cursor + INSERT OR IGNORE)", "interno", "admin"],
    ["S28", "R11", "P10 · ventas", "Resumen de ventas (gRPC `SalesSummary`)", "interno · vía `salesSummary`", "days 1–365, top 1–50", "orders, revenue, top_products", "PERMISSION_DENIED sin rol admin", "interno", "admin"],
    ["S29", "R11", "P10", "Exportar hechos (gRPC `StreamSales`, streaming)", "interno", "after_id, limit", "stream de lotes de 2000 hechos", "Reanudable con `after_id`", "interno", "admin"],
    ["S30", "R05, R08", "P04/P07", "Agregación de consulta GraphQL (`me`, `products`, `product`, `myOrders`, `order`)", "POST /graphql", "documento GraphQL", "data + errors parciales", "Límites de profundidad, costo y página; permisos por campo", "mixto", "Autenticado"],
    ["S31", "R03", "P03", "Mutación `createOrder`", "POST /graphql", "items, notes?, idempotencyKey?", "Order", "Delega en S15", "restringido", "customer"],
    ["S32", "R11", "P10", "`salesSummary`, `syncAnalytics`", "POST /graphql", "days, top", "SalesSummary / int", "Solo admin", "interno", "admin"],
]
w(tabla(["ID", "Req.", "Pantalla y acción", "Propósito", "Verbo y ruta", "Entrada", "Salida", "Reglas y errores", "Clasificación", "Acceso"], S))
w("""
## 1.3 Ejemplos de contrato (datos ficticios, respuestas reales capturadas de la ejecución)

**S15 — crear pedido.** El navegador envía solo productos, cantidades y notas. Si envía `total`, `unit_price` o `status`, se ignoran.

""")
w("```http\nPOST /orders\nContent-Type: application/json\n\n" + json.dumps({"items": [{"product_id": 1, "qty": 2}, {"product_id": 11, "qty": 1}], "notes": "sin cebolla"}, ensure_ascii=False) + "\n```\n")
w("Respuesta (`201`). Subtotal 2 × 2500 + 3200 = 8200; el 2x1 descuenta un taco (2500); total 5700:\n\n" + jbloque(ev("V4a"), 1800))
w("**S34 — promoción del día** (`GET /promotions`, sin sesión):\n\n" + jbloque(ev("F2")))
w("**S14 — contacto con un teléfono inválido** (misma regla que el formulario P03, estado " + str(ev("F4", "estado")) + "):\n\n" + jbloque(ev("F4")))
w("**S04 — catálogo público** (`GET /products?category=Otros`, sin sesión, estado " + str(ev("V1", "estado")) + "):\n\n" + jbloque(ev("V1")))
w("**Error estándar** (todos los servicios usan el mismo formato, con el identificador de correlación):\n\n" + jbloque(ev("V2")))

w("""# Módulo 2 — Clases y cardinalidades del dominio

Diagrama editable: `docs/diagramas/uml_dominio.drawio` (también `.png` y `.svg`). Las cajas punteadas agrupan las clases por el servicio que es autoridad de sus datos.

![UML del dominio y de los servicios públicos](diagramas/uml_dominio.png)

**Leyenda.** Rombo lleno = composición (la parte no existe sin el todo); línea simple = asociación con multiplicidades en ambos extremos; flecha punteada = dependencia de uso (el servicio usa la clase, no implica un registro por cada instancia del servicio). «service» = servicio público; los números S01–S35 corresponden al catálogo del módulo 1.

## 2.1 Relaciones y reglas que las originan

""")
w(tabla(["Origen", "Destino", "Mult. origen", "Mult. destino", "Regla de negocio que la justifica"], [
    ["Cliente", "Usuario", "1", "0..1", "Un cliente puede tener o no acceso con contraseña (altas administrativas no tienen); un usuario cliente apunta exactamente a un cliente y el personal no tiene cliente."],
    ["Usuario", "Sesion", "1", "0..*", "Una persona puede tener varias sesiones abiertas (celular y computador); cada sesión es de un solo usuario y se destruye con él (composición)."],
    ["Cliente", "Pedido", "1", "0..*", "Un cliente puede no haber pedido aún o tener muchos; cada pedido pertenece a un único cliente."],
    ["Pedido", "DetallePedido", "1", "1..*", "Un pedido confirmado contiene al menos un ítem. No existe borrador vacío en el servidor: el carrito vive solo en el navegador y el pedido nace al confirmar."],
    ["Pedido", "EventoPedido", "1", "1..*", "Toda orden registra al menos el evento «creado»; el historial se conserva aunque se anule."],
    ["Producto", "Stock", "1", "1", "Cada producto tiene una sola fila de existencias (en mano y reservado) con la restricción `0 ≤ reservado ≤ enMano`."],
    ["Producto", "Promocion", "1", "0..1", "La promoción del día se define por platillo (hoy «2x1 en Tacos al Pastor»); un producto tiene a lo sumo una promoción (restricción `UNIQUE(product_id)`) y puede no tener ninguna."],
    ["Producto", "DetallePedido", "1", "0..*", "Un producto aparece en muchos pedidos. El detalle copia nombre y precio: si el producto cambia o se da de baja, el historial no cambia."],
    ["Pedido", "Reserva", "1", "1..*", "Cada línea de un pedido reserva stock de un producto (única por pedido y producto). Relación lógica entre servicios por identificador."],
    ["Reserva", "Producto", "0..*", "1", "Un producto puede estar reservado por muchos pedidos a la vez."],
    ["Pedido", "Pago", "1", "0..*", "Un pedido puede no tener pagos aún, o varios intentos si el anterior falló; solo uno puede estar vigente (pendiente o exitoso)."],
    ["Pago", "EventoWebhook", "1", "0..*", "Cada notificación del proveedor se registra una vez (por `event_id`); un pago puede recibir varias (éxito, fallo previo, reintentos)."],
    ["Pedido", "HechoVenta", "1", "0..*", "Un pedido pagado origina un hecho por línea en el servicio de analítica; pedidos no pagados no originan ninguno."],
]))
w("""
Las asociaciones entre clases de servicios distintos (por ejemplo Pedido–Cliente) son referencias por identificador: ningún servicio lee la base de otro.

## 2.2 Correspondencia operación UML ↔ servicio

Cada operación del diagrama lleva al final su ID del módulo 1 (S01–S35). Las operaciones marcadas «interno» (`reservar`, `liberar`, `confirmar`, `introspectar`) no se publican por el gateway.

## 2.3 Modelo interno y DTO

| Dato interno | Sale en respuestas | Motivo |
|---|---|---|
| `claveHash`, `salt`, `tokenHash` | Nunca | Credenciales; solo se conserva hash adaptativo o resumen. |
| `stockLiberado`, `claveIdempotencia`, `ordenSincronizada` | Nunca | Control interno de consistencia. |
| `correo`, `telefono` de Cliente | Solo al dueño y al administrador | Datos personales (módulo 7). |
| `enMano`, `reservado` de Stock | Solo a cocina y administración | El cliente recibe únicamente `in_stock`. |
| `descuento`, `promo` de DetallePedido | Al dueño del pedido, cocina y administración | Explican el total; los calcula el servidor y no se aceptan desde el navegador. |
| `refProveedor` de Pago | Al dueño del pago y al administrador | Referencia, no secreto de la cuenta del comercio. |

## 2.4 Decisiones del equipo

* **¿Carrito y pedido son clases distintas?** Sí. El carrito es estado del navegador (sin servicio); el pedido se crea al confirmar y es la única entidad cuyo precio y total son oficiales.
* **¿Qué pasa con el historial si un producto deja de estar disponible?** El detalle conserva nombre y precio unitario, y la baja del producto es lógica (`active = 0`).
* **¿Qué atributos se conservan internamente y cuáles salen?** Ver tabla 2.3.
* **¿Qué pasa con un pedido si la promoción cambia?** El descuento se copia en el detalle al crear el pedido, igual que el precio: desactivar la promoción afecta solo pedidos nuevos.

# Módulo 3 — Sistemas e integraciones

![Mapa de componentes y despliegue](diagramas/mapa_componentes.png)

Editable: `docs/diagramas/mapa_componentes.drawio`. Líneas naranjas punteadas: lectura de secretos en Vault. Línea verde gruesa: gRPC.

## 3.1 Matriz de sistemas

""")
w(tabla(["Sistema", "Responsabilidad", "Datos bajo su autoridad", "Servicios", "Dependencias", "Contrato de integración", "Credencial o identidad", "Respuesta ante fallos"], [
    ["inventory", "Catálogo, promociones, existencias y reservas. Decide la disponibilidad, el precio y el descuento vigente", "products, stock, promotions, reservations (inventory.db)", "S04–S10, S34, S35", "—", "REST; `POST /reservations`, `/reservations/{id}/release`, `/reservations/{id}/commit` solo para `orders`", "Secreto de arista `edges/inventory/<llamador>` (rotable)", "`UPDATE` condicional atómico: nunca vende de más; reserva idempotente por pedido"],
    ["orders", "Ciclo de vida del pedido y reglas de transición. Decide el estado oficial del pedido", "orders, order_items, order_events, idempotency (orders.db)", "S15–S21", "clients (verifica cliente), inventory (reserva), payments (llama de vuelta)", "REST; `GET /internal/orders/{id}` y `POST /internal/orders/{id}/paid` para `payments`; `GET /internal/orders/export` para `analytics`", "Secretos de arista orders→clients, orders→inventory", "Si inventory o clients caen no crea el pedido (502/503) y no deja reservas; si falla al liberar stock marca `stock_released=0` y S21 lo repara"],
    ["clients", "Perfil y datos personales. Decide qué ve cada actor de un cliente", "clients (clients.db)", "S11–S14", "—", "REST; `POST /internal/clients` solo para `auth`", "Secretos de arista", "Cierra con 404 al no dueño; vista reducida (id, nombre) para cocina"],
    ["payments", "Inicio de pagos, verificación y deduplicación de avisos del proveedor. Decide el estado del pago y es el único que pide marcar un pedido como pagado", "payments, webhook_events (payments.db)", "S22–S26", "orders", "REST; webhook con firma HMAC", "Secreto de arista payments→orders; secreto `mariachi/payments` (HMAC del proveedor)", "Si `orders` no responde: el pago queda `succeeded` con `order_synced=0`, responde 200 «pending» y se reintenta con el aviso duplicado o con S26"],
    ["auth", "Cuentas, sesiones, introspección", "users, sessions, login_failures (auth.db)", "S01–S03, S33", "clients (alta de perfil)", "REST privado para el gateway", "Secretos de arista api-gateway→auth, auth→clients", "Registro con usuario pendiente y compensación: si `clients` falla, el usuario no queda creado"],
    ["analytics", "Proyección de ventas y entrega por gRPC", "sales_facts (analytics.db)", "S27–S29", "orders", "gRPC (`analytics.proto`)", "Metadatos con secreto de arista graphql-gateway→analytics + rol admin", "Si cae, GraphQL devuelve error parcial en ese campo"],
    ["graphql-gateway", "Agregación de lectura y mutación `createOrder`", "ninguno (sin base)", "S30–S32", "orders, inventory, clients, payments, analytics", "GraphQL privado", "Identidad verificada propagada + secretos de arista", "Errores parciales por campo"],
    ["api-gateway", "Frontera pública: enrutamiento, autenticación, roles, límites", "ninguno", "todas las rutas externas", "auth, graphql-gateway y servicios", "Tabla de rutas explícita", "Aristas hacia cada destino", "401, 403, 404, 405, 413, 415, 429, 502, 503, 504, 500 (Vault)"],
]))
w("""
## 3.2 Intercambios principales

* **Reserva de stock.** `orders` pide una reserva atómica a `inventory` antes de aceptar el pedido y usa los precios y descuentos devueltos (datos mínimos: id de pedido, producto y cantidad de ida; precio, descuento y nombre de vuelta); si la respuesta no llega, el pedido no se crea. Si el guardado local fallara tras reservar, se libera la reserva (compensación).
* **Pago.** Se verifica el aviso con HMAC-SHA256 calculado sobre el cuerpo recibido, con el secreto guardado en Vault. Cada `event_id` se registra una sola vez (clave primaria), de modo que un duplicado devuelve 200 sin efectos. Solo `payments` autoriza el cambio a «pagado», y `orders` lo acepta únicamente si el monto coincide y el pedido está pendiente. El frontend no decide el estado.
* **Sistemas complementarios.** El proveedor de pagos se reemplaza por un adaptador de prueba (`scripts/smoke_e2e.py` y `tests/support/helpers.py` firman eventos con el mismo contrato). No hay despacho, boletas ni mensajería (brecha B4).

## 3.3 Secuencia de un flujo representativo

![Secuencia: crear pedido y pagar](diagramas/secuencia_pedido_pago.png)

Fuente editable: `docs/diagramas/secuencia_pedido_pago.mmd` (draw.io la importa con Organizar → Insertar → Avanzado → Mermaid).

# Módulo 4 — Stakeholders y permisos HTTP

## 4.1 Registro de stakeholders

""")
w(tabla(["Stakeholder", "Interés", "Rol asociado", "Uso de información"], [
    ["Visitante anónimo", "Conocer la carta y los precios", "anónimo", "Solo catálogo público (S04, S05)"],
    ["Cliente registrado (Camila, Matías)", "Pedir, pagar y seguir sus pedidos", "`customer`", "Sus datos, sus pedidos y sus pagos"],
    ["Personal de cocina", "Preparar pedidos pagados y controlar insumos", "`kitchen`", "Pedidos pagados, nombre del cliente, existencias; sin correo, teléfono ni pagos"],
    ["Dueño / administrador (Benjamín)", "Gestionar carta, stock, clientes y ventas", "`admin` (también `customer`)", "Todos los datos del negocio"],
    ["Proveedor de pagos", "Notificar resultados de cobro", "Identidad técnica (firma HMAC)", "Solo el webhook, sin sesión"],
    ["Servicios internos", "Colaborar entre sí", "Identidades técnicas (`api-gateway`, `graphql-gateway`, `orders`, `payments`, `auth`, `analytics`)", "Solo las aristas autorizadas del módulo 6"],
    ["Seguidores en redes sociales y reseñas", "Conocer el restaurante", "**sin permisos operativos**", "Reciben información pública del frontend estático (P05); no invocan servicios"],
    ["Contabilidad / autoridad tributaria", "Boletas y reportes", "**sin permisos operativos**", "Reciben información a través del administrador (S28/S29); las boletas no están implementadas"],
    ["Equipo docente", "Evaluar", "**sin permisos operativos**", "Recibe este informe y el código; no accede a datos de clientes"],
]))
w("""
## 4.2 Matriz de permisos por ruta, verbo y condición

Convención: ✔ permitido, ✘ denegado, — no aplicable. «Se verifica en» indica dónde se aplica la decisión (el servicio privado siempre repite la comprobación de rol y propiedad).

""")
w(tabla(["Servicio", "Ruta", "Verbo", "Visitante", "customer", "kitchen", "admin", "Condición", "Se verifica en"], [
    ["S04/S05", "/products, /products/{id}", "GET", "✔ campos públicos", "✔ públicos", "✔ + stock", "✔ + stock", "Solo activos para no personal", "gateway (ruta pública) e inventory (campos)"],
    ["S06–S08", "/products, /products/{id}", "POST, PATCH, DELETE", "✘ 401", "✘ 403", "✘ 403", "✔", "—", "gateway y inventory"],
    ["S34", "/promotions", "GET", "✔ vigentes", "✔ vigentes", "✔ vigentes", "✔ todas", "—", "gateway (ruta pública) e inventory"],
    ["S35", "/promotions/{id}", "PATCH", "✘ 401", "✘ 403", "✘ 403", "✔", "Solo cambia `active`", "gateway e inventory"],
    ["S09/S10", "/stock, /stock/{id}/adjust", "GET, POST", "✘ 401", "✘ 403", "✔", "✔", "Ajuste no puede bajar de lo reservado", "gateway e inventory"],
    ["S11/S13", "/clients", "GET, POST", "✘ 401", "✘ 403", "✘ 403", "✔", "—", "gateway y clients"],
    ["S12", "/clients/{id}", "GET", "✘ 401", "✔ solo el propio (otro → 404)", "✔ solo id y nombre", "✔ completo", "Propiedad del recurso", "clients"],
    ["S14", "/clients/{id}", "PATCH", "✘ 401", "✔ solo el propio", "✘ 403", "✔", "Propiedad", "gateway y clients"],
    ["S15", "/orders", "POST", "✘ 401", "✔ con cliente asociado", "✘ 403", "✘ 403", "Precio y total del servidor; stock reservado", "gateway y orders"],
    ["S16", "/orders", "GET", "✘ 401", "✔ solo propios", "✔ pagados, preparando, listos", "✔ todos", "Alcance por rol", "orders"],
    ["S17", "/orders/{id}", "GET", "✘ 401", "✔ solo propio (ajeno → 404)", "✔", "✔", "Propiedad", "orders"],
    ["S18", "/orders/{id}/cancel", "POST", "✘ 401", "✔ propio y pendiente de pago", "✘ 403", "✔ hasta antes de preparar", "Estado del pedido", "gateway y orders"],
    ["S19", "/orders/{id}/status", "PATCH", "✘ 401", "✘ 403", "✔", "✔", "Solo transiciones válidas", "gateway y orders"],
    ["S20/S21", "/orders/expire-pending, /orders/reconcile-stock", "POST", "✘ 401", "✘ 403", "✘ 403", "✔", "—", "gateway y orders"],
    ["S22", "/payments", "POST", "✘ 401", "✔ solo pedidos propios", "✘ 403", "✘ 403", "Pedido pendiente; clave de idempotencia", "gateway y payments"],
    ["S24/S25", "/payments, /payments/{id}", "GET", "✘ 401", "✔ solo propios", "✘ 403", "✔", "Propiedad", "gateway y payments"],
    ["S26", "/payments/reconcile", "POST", "✘ 401", "✘ 403", "✘ 403", "✔", "—", "gateway y payments"],
    ["S23", "/payments/webhook", "POST", "✔ solo con firma HMAC válida", "—", "—", "—", "Firma, monto y event_id", "payments"],
    ["S30–S32", "/graphql", "POST", "✘ 401", "✔ operaciones y campos propios", "✔ campos de staff", "✔", "Autorización por campo (módulo 8)", "gateway y graphql-gateway"],
    ["Todos", "cualquier ruta anterior", "PUT", "—", "—", "—", "—", "No aplicable: 405", "gateway"],
    ["Interno", "/reservations, /internal/*", "todos", "✘", "✘", "✘", "✘", "No publicadas (404); los servicios exigen el secreto de la arista", "gateway y servicio"],
]))
w("""
Los verbos que no aparecen para una ruta son **no aplicables** y el gateway responde 405 (por ejemplo DELETE sobre pedidos: la anulación se expresa con `POST /orders/{id}/cancel`).

**Identidades técnicas** (no son usuarios; se autentican con el secreto de su arista, módulo 6):

""")
w(tabla(["Identidad", "Servicio y ruta", "Verbo", "Decisión", "Alcance y condición", "Se verifica en"], [
    ["api-gateway", "todos los servicios, rutas de la tabla 6.1", "según tabla", "✔", "Solo con identidad de usuario verificada por `auth`", "cada servicio (`make_guard`)"],
    ["graphql-gateway", "orders, inventory, clients, payments (lectura y `POST /orders`); analytics (gRPC)", "GET, POST", "✔", "Propaga la identidad del usuario; no lee bases de datos", "cada servicio e interceptor gRPC"],
    ["orders", "inventory `/reservations`, `/reservations/{id}/release`, `/reservations/{id}/commit`; clients `GET /clients/{id}`", "POST, GET", "✔", "Solo para pedidos propios del flujo", "inventory, clients"],
    ["payments", "orders `GET /internal/orders/{id}`, `POST /internal/orders/{id}/paid`", "GET, POST", "✔", "Pedido pendiente y monto igual al total", "orders"],
    ["analytics", "orders `GET /internal/orders/export`", "GET", "✔", "Solo hechos de pedidos pagados, sin datos personales", "orders"],
    ["auth", "clients `POST /internal/clients`", "POST", "✔", "Solo durante el registro", "clients"],
    ["Proveedor de pagos", "`POST /payments/webhook`", "POST", "✔", "Firma HMAC válida, `event_id` nuevo, monto correcto", "payments"],
    ["cualquier otra combinación", "—", "—", "✘ 403", "Llamador fuera de la topología", "servicio de destino"],
]))
w("""
Una **anulación no borra** el registro: el pedido pasa a `cancelado` o `expirado` y su historial de eventos se conserva. Ocultar un botón no otorga ni quita permisos: todas las decisiones anteriores son del backend (casos de prueba en el módulo 10).

# Módulo 5 — Clases del API Gateway

![UML del API Gateway, políticas y GraphQL Gateway](diagramas/uml_gateway.png)

Editable: `docs/diagramas/uml_gateway.drawio`. Correspondencia con el código:

""")
w(tabla(["Clase UML", "Implementación"], [
    ["ApiGateway", "`services/api_gateway/main.py` (`create_app`)"],
    ["RouteDefinition", "`services/api_gateway/routes.py` (`Route`, tabla `ROUTES`)"],
    ["AuthenticationPolicy", "función `authenticate` del gateway + `POST /introspect` de `auth`; descarte de cabeceras de identidad al construir la solicitud interna"],
    ["AuthorizationPolicy", "campo `roles` de cada `Route`"],
    ["RateLimiter", "`RateLimiter` del gateway (ventana de 60 s por IP y categoría)"],
    ["ServiceTarget", "`common/calls.py` (`ServiceClient`)"],
    ["SecretProvider / VaultClient", "`common/vault.py`"],
    ["ServiceGuard", "`common/security.py` (`make_guard`)"],
    ["GraphQLGateway, Schema, Resolver, DataLoader, CostLimit/DepthLimit", "`services/graphql_gateway/` (`main.py`, `schema.py`, `limits.py`)"],
    ["AnalyticsClient / AnalyticsServer", "`services/analytics/client.py`, `server.py`, `analytics.proto`"],
]))
w("""
## 5.1 Cuántos gateways y por qué

Se usan **dos**, con funciones distintas: un **API Gateway externo** (única puerta pública; enrutamiento, sesión, roles, límites) y un **GraphQL Gateway privado** (composición de lectura entre cuatro servicios, con su propio esquema de autorización). Unirlos obligaría a que el borde público conociera los esquemas de datos y los límites de agregación; separarlos permite exponer REST transaccional y la agregación con políticas diferentes. No se justifica un tercer gateway (por ejemplo, uno administrativo): las rutas administrativas se separan por política de rol.

## 5.2 Clasificación de rutas

* **Externas anónimas:** `POST /auth/register`, `POST /auth/login`, `GET /products`, `GET /products/{id}` (identidad opcional), `POST /payments/webhook` (firma).
* **Externas autenticadas:** `/auth/me`, `/auth/logout`, pedidos, pagos, clientes, `/graphql`.
* **Administrativas:** escritura de productos, `/stock`, `/clients` (listado y alta), `expire-pending`, `reconcile-*`.
* **Internas (nunca publicadas):** `/reservations/*`, `/internal/*`, introspección y todo gRPC.

## 5.3 Qué valida cada capa

| Capa | Valida |
|---|---|
| API Gateway | Ruta y verbo permitidos (lista explícita; lo demás es 404/405), sesión (introspección en cada solicitud), rol, límite de tasa, tamaño (64 KiB), `Content-Type` JSON, tiempo de espera de 3 s, descarte de cabeceras de identidad y construcción de las propias, `X-Request-Id` nuevo. |
| Servicios privados | Que el llamador sea una identidad técnica autorizada con el secreto de su arista (403 si no); rol; propiedad del recurso; reglas de negocio, estados e integridad (restricciones en la base). |
| GraphQL Gateway | Profundidad, costo, tamaño de página, permisos por campo, introspección apagada, un lote por tipo de dato. No toca bases de datos. |

## 5.4 Recorrido de una solicitud autorizada y de una denegada

![Secuencia: solicitud denegada](diagramas/secuencia_denegada.png)

**Autorizada:** diagrama del módulo 3.3 (cliente crea su pedido). **Denegada:** Matías pide el pedido de Camila; `orders` compara `client_id` y responde 404 sin datos (evidencia V4c). Sin cookie, el gateway corta con 401 antes de llamar a ningún servicio (prueba `test_gateway_corta_antes_de_llamar_al_servicio`).

Tiempos de espera: 3 s por llamada REST y un reintento solo en GET; gRPC 5 s (unary) y 30 s (sync). Errores controlados: 401, 403, 404, 405, 413, 415, 429, 502, 503, 504; fallo de Vault en el gateway → 500; en servicios privados → 503 (falla cerrado). Los registros no contienen secretos (evidencia L2).

# Módulo 6 — Rutas y secretos de integración

## 6.1 Matriz de rutas

Generada desde `services/api_gateway/routes.py`, de modo que el informe coincide con la implementación.

""")
DEST = {
    "payments": "payments", "inventory": "inventory", "clients": "clients", "orders": "orders", "graphql-gateway": "graphql-gateway",
}
CTRL = {"public": "límite de tasa; firma HMAC en el servicio", "optional": "límite de tasa; identidad solo si la cookie es válida", "session": "sesión + rol; límite de tasa"}
filas = [
    ["R-01", "externo", "POST", "/auth/register", "anónimo", "auth /register", "validación, límite 5/min por IP", f"`{edge_path('auth','api-gateway')}`"],
    ["R-02", "externo", "POST", "/auth/login", "anónimo", "auth /login", "límite 10/min por IP; bloqueo por usuario", f"`{edge_path('auth','api-gateway')}`"],
    ["R-03", "externo", "POST", "/auth/logout", "sesión", "auth /logout", "revoca en servidor y borra cookie", f"`{edge_path('auth','api-gateway')}`"],
    ["R-04", "externo", "GET", "/auth/me", "sesión", "auth /introspect", "—", f"`{edge_path('auth','api-gateway')}`"],
]
n = 5
for r in ROUTES:
    acceso = {"public": "anónimo", "optional": "anónimo (identidad opcional)", "session": "sesión"}[r.access]
    if r.roles:
        acceso += " · " + ", ".join(r.roles)
    filas.append([f"R-{n:02d}", "externo", r.method, r.pattern, acceso, f"{r.upstream} {r.path}", CTRL[r.access], f"`{edge_path(r.upstream, 'api-gateway')}`"])
    n += 1
w(tabla(["ID", "Gateway", "Verbo", "Ruta externa", "Acceso y rol", "Destino interno", "Controles", "Referencia de credencial"], filas))
w("""
Transformaciones: el gateway elimina la cookie, las cabeceras de identidad del navegador y cualquier cabecera no listada (solo reenvía `Content-Type`, `Idempotency-Key`, `X-Signature` y `Accept`); agrega `X-Service-Caller`, `X-Service-Token`, `X-Request-Id` y la identidad verificada (`X-User-Id`, `X-Username`, `X-Roles`, `X-Client-Id`). La credencial del usuario (cookie opaca) nunca viaja a los servicios: la credencial entre sistemas es el secreto de arista.

## 6.2 Operaciones GraphQL

Todas entran por R-%02d (`POST /graphql`, gateway externo) y se resuelven en el **GraphQL Gateway privado**, que llama a los servicios con sus propios secretos de arista (`mariachi/edges/<servicio>/graphql-gateway`). Que la ruta esté permitida no autoriza todas las operaciones: cada operación y campo tiene su control.

""" % (4 + 1 + [i for i, r in enumerate(ROUTES) if r.pattern == "/graphql"][0]))
w(tabla(["Operación", "Tipo", "Campos y autorización", "Resolver", "Subsistemas"], [
    ["`me`", "Query", "Identidad propia; `client` del propio usuario", "`Query.me`", "clients"],
    ["`products(first, after, category)`", "Query", "Públicos; `stock` solo kitchen/admin (`IsStaff`)", "`Query.products`, `Product.stock`", "inventory"],
    ["`product(id)`", "Query", "ídem", "`Query.product` (DataLoader)", "inventory"],
    ["`myOrders(first, after, status)`", "Query", "Pedido con `subtotal`, `discount`, `total` e ítems con `discount`/`promo`. Solo pedidos del alcance del rol; `client.email/phone` solo dueño/admin (`OwnerOrAdmin`); `payment` solo customer/admin (`CanPay`)", "`Query.myOrders`, `Order.client`, `Order.payment`, `OrderItem.product`", "orders, clients, inventory, payments"],
    ["`order(id)`", "Query", "ídem; pedido ajeno → `null`", "`Query.order`", "orders (+ lotes)"],
    ["`salesSummary(days, top)`", "Query", "Solo admin (`IsAdmin`)", "`Query.sales_summary`", "analytics (gRPC)"],
    ["`createOrder(items, notes, idempotencyKey)`", "Mutation", "Solo customer (lo exige `orders`)", "`Mutation.create_order`", "orders"],
    ["`syncAnalytics`", "Mutation", "Solo admin", "`Mutation.sync_analytics`", "analytics (gRPC)"],
]))
w("\n## 6.3 Métodos gRPC\n\nContrato: `services/analytics/analytics.proto` (paquete `mariachi.analytics.v1`).\n\n")
w(tabla(["Servicio.método", "Entrada", "Salida", "Modalidad", "Identidad permitida", "Plazo máximo"], [
    ["Analytics.Health", "Empty", "HealthReply", "unary", "sin credencial (health check)", "2 s"],
    ["Analytics.Sync", "Empty", "SyncReply{imported}", "unary", "graphql-gateway con rol admin", "30 s"],
    ["Analytics.SalesSummary", "SummaryRequest{days, top}", "SummaryReply", "unary", "graphql-gateway con rol admin", "5 s"],
    ["Analytics.StreamSales", "StreamRequest{after_id, limit}", "stream SalesBatch{facts[≤2000], last_id}", "server streaming", "graphql-gateway con rol admin", "sin plazo global; cancelable; reanudable con `after_id`"],
]))
w("""
## 6.4 Inventario simbólico de secretos e identidades

Solo referencias simbólicas; los valores se generan con `secrets.token_urlsafe(32)` al ejecutar `scripts/vault_bootstrap.py` y **no existen en el repositorio, en el informe ni en el navegador**. Cada arista tiene su propio secreto (prueba `test_secretos_distintos_por_integracion`).

""")
sec = []
for caller, callee in EDGES:
    sec.append([f"`{edge_path(callee, caller)}`", "Credencial de servicio (arista)", "bootstrap (Vault)", caller, f"Autenticar {caller} ante {callee}", "Vault KV v2", f"Solo llamadas permitidas a {callee}", "Rotar con gracia (token anterior vigente) y revocar el anterior"])
sec.append(["`mariachi/payments` (webhook_hmac)", "Secreto compartido HMAC", "bootstrap (Vault); se entrega al proveedor", "payments", "Verificar avisos del proveedor", "Vault KV v2", "Solo la política de `payments` puede leerlo", "`--rotate-webhook` y luego `--revoke-previous-webhook`"])
sec.append(["Token de Vault por servicio (`/run/vault/token`)", "Token con política de mínimo privilegio", "bootstrap", "cada servicio", "Leer solo sus secretos", "Volumen montado de solo lectura en cada contenedor", "Un servicio no puede leer secretos ajenos (prueba `test_vault_minimo_privilegio_por_servicio`)", "Re-ejecutar el bootstrap emite tokens nuevos; revocar los anteriores en Vault"])
sec.append(["`VAULT_ROOT_TOKEN` (`.env`)", "Token raíz de desarrollo", "operador", "bootstrap", "Crear políticas y secretos", "`.env` no versionado (`.gitignore`)", "Solo el contenedor `vault-bootstrap`", "En producción: no usar token raíz ni modo dev"])
sec.append(["Cookie `session_token`", "Token de sesión opaco", "auth", "navegador → api-gateway", "Identificar la sesión", "Navegador (HttpOnly); en servidor solo su SHA-256", "15 minutos", "`/auth/logout` revoca; expira sola"])
sec.append(["`DEMO_PASSWORD` (`.env`)", "Clave de usuarios de prueba", "operador", "auth (siembra)", "Datos de prueba", "`.env` no versionado", "Solo entornos de prueba", "Cambiar `.env` y recrear volúmenes"])
w(tabla(["Referencia", "Tipo", "Emisor", "Consumidor", "Finalidad", "Ubicación segura", "Alcance", "Rotación y revocación"], sec))
w("""
**Qué hacer si una clave se filtra.** (1) `python scripts/vault_bootstrap.py --rotate-edge <llamador> <destino>` genera un secreto nuevo y deja el anterior como `previous` (ventana de gracia sin cortar el servicio); (2) tras confirmar que el llamador usa el nuevo, `--revoke-previous-edge` lo invalida (prueba `test_rotacion_con_gracia_y_revocacion`); (3) lo mismo para el secreto del webhook (prueba `test_rotacion_del_secreto_del_webhook`). **Si Vault no responde**, los servicios fallan cerrado: el gateway responde 500 y los servicios privados 503; el caché de secretos (TTL 30 s) evita consultar en cada llamada (prueba `test_vault_caido_falla_cerrado`).

**Identidad confiable para propiedad.** El gateway propaga `X-User-Id/X-Client-Id` solo después de la introspección; los servicios aceptan esas cabeceras únicamente de un llamador que presentó el secreto de su arista, por lo que el navegador no puede falsificarlas (prueba `test_cliente_no_puede_inyectar_identidad_ni_roles`).

**TLS.** Los secretos y datos restringidos deben viajar por TLS. En esta entrega el borde público se asume terminado por un proxy TLS delante del gateway (cookie `Secure` con `COOKIE_SECURE=1`) y la red privada es una red de contenedores aislada (`internal: true`). No hay mTLS entre servicios (ver limitaciones).

# Módulo 7 — Datos sensibles y secretos del cliente

## 7.1 Matriz de datos

""")
w(tabla(["Dato o credencial", "Finalidad", "Clasificación", "Sistema custodio", "Roles autorizados", "Representación en el frontend", "Protección", "Retención"], [
    ["Nombre, categoría, precio de platillo", "Mostrar la carta", "Público", "inventory", "Todos", "P02", "Validación de entrada; solo admin escribe", "Mientras exista (baja lógica)"],
    ["Existencias (en mano, reservado)", "Operación del local", "Interno", "inventory", "kitchen, admin", "P09/P10", "Campo omitido para clientes y anónimos", "Mientras exista el producto"],
    ["Nombre del cliente", "Identificar el pedido", "Personal", "clients", "dueño, admin, kitchen", "P03/P04", "Vista reducida para cocina", "Mientras exista la cuenta"],
    ["Correo y teléfono", "Contacto del pedido", "Personal restringido", "clients", "dueño, admin", "P03/P04", "Nunca en catálogo; omitidos para cocina; excluidos de logs; autorización por campo en GraphQL", "Mientras exista la cuenta"],
    ["Contraseña", "Autenticación", "Credencial", "auth", "ninguno (no se devuelve)", "P06 (campo de entrada)", "scrypt (N=2¹⁴, r=8, p=1) con sal aleatoria de 16 bytes; comparación en tiempo constante; no se registra", "Mientras exista la cuenta"],
    ["Token de sesión", "Mantener la sesión", "Credencial", "auth (hash SHA-256)", "dueño", "Cookie HttpOnly", "Opaco, 15 min, revocable; el servidor guarda solo el hash", "15 min"],
    ["Pedido (ítems, total, notas)", "Operación y comprobante", "Personal restringido", "orders", "dueño, kitchen, admin", "P04/P07", "Propiedad por `client_id`; 404 para ajenos", "Se conserva (historial, contabilidad)"],
    ["Pago (monto, referencia)", "Cobro", "Restringido", "payments", "dueño, admin", "P08", "Propiedad; sin datos de tarjeta", "Se conserva (contabilidad)"],
    ["Datos de tarjeta", "—", "No se manejan", "Proveedor de pagos", "—", "—", "El comercio nunca los recibe", "—"],
    ["Secreto HMAC del proveedor", "Autenticar avisos", "Secreto de integración", "Vault", "payments", "Nunca", "Vault + política mínima", "Rotación"],
    ["Secretos de arista y tokens de Vault", "Autenticar servicios", "Secreto de integración", "Vault", "El servicio dueño", "Nunca", "Módulo 6", "Rotación"],
]))
w("""
## 7.2 Decisión sobre secretos del cliente

**No se custodian secretos del cliente** más allá de su contraseña (que se guarda solo como hash adaptativo con sal). No se almacenan números de tarjeta, claves de API del cliente ni tokens de pago reutilizables: el cobro lo hace el proveedor y el comercio solo recibe un aviso firmado con el resultado. Un correo o teléfono es dato personal restringido, no una clave. Un navegador no puede guardar confidencialmente una clave compartida, por eso el frontend no recibe ninguna: usa únicamente la cookie de sesión opaca e HttpOnly.

## 7.3 Recorrido de un dato restringido (el correo)

1. **Captura:** `POST /auth/register` (S01) por TLS; el gateway valida forma y tamaño y lo reenvía a `auth`.
2. **Alta:** `auth` pide el perfil a `clients` con el secreto de la arista `auth→clients`; el correo se normaliza a minúsculas y es único.
3. **Almacenamiento:** `clients.db`; nunca en `auth`, `orders` ni `analytics`.
4. **Consulta:** el dueño y el administrador lo ven (S12, GraphQL `email`); cocina recibe solo id y nombre; GraphQL repite la regla por campo.
5. **Logs:** no se registra (los logs llevan `user_id` seudónimo y el hash corto de un nombre de usuario fallido).
6. **Conservación y eliminación:** se conserva mientras exista la cuenta; los pedidos y pagos se retienen por razones contables y de historial. **El borrado o la anonimización de una cuenta no está implementado** (limitación declarada); el procedimiento propuesto es anonimizar el perfil (reemplazar nombre, correo y teléfono) conservando el `client_id` de los pedidos.

## 7.4 Casos de validación ejecutados

Cada fila es una ejecución real contra el sistema levantado (`docs/evidencia/capturar.py` → `ejecuciones.json`) y está respaldada por una prueba automatizada.

""")
def fila(clave, entrada, identidad, esperado, comp, tests):
    return [clave, entrada, identidad, esperado, f"{EV[clave]['estado']}: " + json.dumps(EV[clave]['respuesta'], ensure_ascii=False)[:90].replace("|", "/"), comp, tests]
w(tabla(["Caso", "Entrada", "Identidad", "Resultado esperado", "Resultado obtenido", "Verifica", "Prueba automatizada"], [
    fila("V1", "GET /products?category=Otros", "anónimo", "200 con campos públicos", "api-gateway (ruta pública) + inventory", prueba("test_catalogo_publico_para_visitantes_solo_campos_publicos")),
    fila("V2", "GET /orders", "sin sesión", "401", "api-gateway", prueba("test_sin_sesion_y_con_cookie_falsa_401")),
    fila("V3", "POST /products", "camila (customer)", "403", "api-gateway e inventory", prueba("test_matriz_de_permisos_http", "test_gateway_corta_antes_de_llamar_al_servicio")),
    fila("V4b", f"GET /orders/<pedido de camila>", "camila (dueña)", "200 con el pedido", "orders (propiedad)", prueba("test_propiedad_de_ordenes_entre_clientes")),
    fila("V4c", f"GET /orders/<pedido de camila>", "matias (customer)", "404 sin datos", "orders (propiedad)", prueba("test_propiedad_de_ordenes_entre_clientes")),
    fila("V5a", "GET orders:/orders directo", "sin secreto de servicio", "403", "orders (guardia de llamador)", prueba("test_servicios_privados_rechazan_llamadas_sin_credencial")),
    fila("V5c", "POST /products con cabeceras `X-Roles: admin` y `X-User-Id` inventadas", "camila (customer)", "403", "api-gateway (descarta cabeceras de identidad)", prueba("test_cliente_no_puede_inyectar_identidad_ni_roles")),
    fila("V5b", "GET inventory:/products con el secreto de otra arista", "orders→inventory declarando ser graphql-gateway", "403", "inventory", prueba("test_token_de_otra_arista_no_sirve")),
    fila("V6b", "POST /payments/webhook firma incorrecta", "proveedor falso", "401", "payments (HMAC)", prueba("test_firma_invalida_o_ausente")),
    fila("V6c", "Webhook con monto alterado", "proveedor", "409", "payments", prueba("test_monto_distinto_es_rechazado")),
    fila("V6d", "PATCH /orders/{id}/status", "camila intenta marcar el avance", "403", "api-gateway y orders", prueba("test_matriz_de_permisos_http")),
    fila("V6e", "POST /internal/orders/{id}/paid", "camila", "404 (no publicada)", "api-gateway", prueba("test_rutas_internas_no_salen_por_el_gateway")),
    fila("F4", "PATCH /clients/CLI-001 con teléfono `12345`", "camila", "422", "clients (validación del servidor)", prueba("test_p03_formulario_del_frontend_valida_contacto_en_el_servidor")),
]))
w("""
# Módulo 8 — Separación privada y agregaciones GraphQL

## 8.1 Mapa de clasificación

""")
w(tabla(["Servicio", "Naturaleza", "Responsabilidad", "Datos propios", "Contrato", "Dependencias", "Justificación de la separación"], [
    ["auth", "Transaccional (identidad)", "Cuentas y sesiones", "users, sessions", "REST privado", "clients", "Los datos de credenciales tienen una superficie de riesgo distinta de los datos del negocio y rotan por separado."],
    ["inventory", "Transaccional", "Catálogo, stock y reservas", "products, stock, reservations", "REST", "—", "Alta cohesión: la regla «no vender más de lo que hay» exige que catálogo y existencias se actualicen en una sola transacción."],
    ["clients", "Transaccional", "Perfil y datos personales", "clients", "REST", "—", "Concentra el dato personal en un único custodio con política propia; los demás servicios solo guardan el identificador."],
    ["orders", "Transaccional", "Pedidos y transiciones", "orders, order_items, order_events", "REST", "inventory, clients", "Autoridad del estado del pedido; su ritmo de cambio (flujo de cocina) difiere del catálogo."],
    ["payments", "Transaccional", "Pagos y avisos del proveedor", "payments, webhook_events", "REST + webhook", "orders", "Aísla la integración con el proveedor y su secreto: una credencial con permisos mínimos."],
    ["graphql-gateway", "Agregación", "Componer lecturas para pantallas", "— (sin base)", "GraphQL", "orders, inventory, clients, payments, analytics", "Evita N+1 y llamadas múltiples desde el navegador sin duplicar reglas de negocio."],
    ["analytics", "Analítica / alta demanda", "Proyección de ventas y entrega masiva", "sales_facts", "gRPC", "orders", "Separa la lectura analítica de las transacciones; admite streaming y su propio retraso aceptado (sincronización cada 60 s)."],
    ["api-gateway", "Borde público", "Enrutamiento y políticas", "—", "REST", "todos", "Única superficie pública."],
]))
w("""
No se dividió un servicio por tabla ni por pantalla: `orders` conserva pedido, detalle y eventos; `inventory` conserva producto, stock y reserva. Cada servicio solo escribe en su propia base; las colaboraciones son contratos explícitos.

## 8.2 Schema GraphQL

Archivo: `docs/schema.graphql` (exportado del código).

""")
w("```graphql\n" + (ROOT / "docs/schema.graphql").read_text() + "```\n")
w("""
## 8.3 Límites y controles

| Control | Valor | Dónde |
|---|---|---|
| Profundidad máxima | 6 (configurable) | `QueryDepthLimiter` |
| Costo máximo | 5000 (nodos ponderados por `first` y por listas anidadas) | `limits.py`, regla de validación previa a la ejecución |
| Tamaño de página | 1–50; cursor opaco inválido → error | `schema.py` |
| Introspección | Deshabilitada | `NoSchemaIntrospectionCustomRule` |
| Lotes de operaciones y GET | No permitidos | Strawberry (sin batching) y `allow_queries_via_get=False` |
| Batching de datos | Un lote por tipo (clientes, productos, pagos) por solicitud | `DataLoader` |
| Errores | Parciales por campo; los inesperados se enmascaran | `MaskErrors` |
| Plazos | 3 s por llamada interna, 5 s gRPC | `ServiceClient`, `AnalyticsClient` |

## 8.4 Consulta de prueba y respuesta (ejecución real)

""")
w("```graphql\n{ myOrders(first: 10) { total nextCursor nodes { id status subtotal discount total notes\n    client { id name email }\n    items { name qty unitPrice discount product { name category inStock } }\n    payment { status amount } } } }\n```\n")
w("Respuesta (G1):\n\n" + jbloque(ev("G1"), 2200))
w("Llamadas internas generadas por esa única consulta (G1b): `" + "`, `".join(f"{c[1]} {c[0]}{c[2]}" for c in EV["G1b"]["llamadas"]) + "`. Hay una llamada por subsistema: no hay N+1 (prueba `test_batching_evita_n_mas_1`, que además usa 5 pedidos de 3 líneas).\n\n")
w("## 8.5 Matriz de autorización\n\n")
w(tabla(["Campo", "Visitante", "customer", "kitchen", "admin", "Mecanismo"], [
    ["Order.* (propios)", "✘ 401", "✔ solo los propios", "✔ pagados, preparando, listos", "✔", "El servicio `orders` filtra por identidad; el gateway no confía en el resolver"],
    ["Order.client.name", "✘", "✔ propio", "✔", "✔", "Vista del servicio `clients`"],
    ["Client.email, Client.phone", "✘", "✔ propio", "✘ error de campo", "✔", "`OwnerOrAdmin` + vista reducida en `clients`"],
    ["Order.payment", "✘", "✔ propio", "✘ error de campo", "✔", "`CanPay` + propiedad en `payments`"],
    ["Product.stock", "✘", "✘ error de campo", "✔", "✔", "`IsStaff` + omisión en `inventory`"],
    ["salesSummary, syncAnalytics", "✘", "✘ error", "✘ error", "✔", "`IsAdmin` + interceptor gRPC"],
]))
w("""
## 8.6 Evidencia de ejecución

""")
w(tabla(["Caso", "Qué demuestra", "Resultado", "Prueba"], [
    ["G2", "customer pide `stock`", f"`stock: null` y error «{ev('G2')['errors'][0]['message']}»", prueba("test_autorizacion_por_campo")],
    ["G3", "kitchen pide `stock`", f"`available: {ev('G3')['data']['product']['stock']['available']}`", prueba("test_autorizacion_por_campo")],
    ["V4d", "Pedido ajeno por GraphQL", "`order: null`", prueba("test_no_se_ve_la_orden_de_otro_cliente")],
    ["G4", "6 alias de `myOrders(first: 50)`", ev("G4")["errors"][0]["message"], prueba("test_limite_de_costo_rechaza_consultas_abusivas")],
    ["G5", "`first: 51`", ev("G5")["errors"][0]["message"], prueba("test_limites_de_pagina_y_cursor_invalido")],
    ["(prueba)", "Profundidad", "Rechazo al superar el máximo configurado", prueba("test_limite_de_profundidad")],
    ["G6", "Introspección", "Rechazada", prueba("test_introspeccion_deshabilitada_y_get_no_permitido")],
    ["G7", "`clients` caído", "`client: null`, datos de `orders` intactos, error en la ruta `myOrders.nodes.0.client`", prueba("test_errores_parciales_si_clientes_no_responde", "test_errores_parciales_si_inventario_no_responde")],
    ["—", "Sin sesión / sin secreto de servicio", "401 / 403", prueba("test_graphql_exige_sesion_y_llamador_autorizado")],
]))
w("""
**Frontend.** Por la instrucción del docente no se ejecuta desde el navegador; se evidencia con los datos del frontend (módulo 10.4). Para la pantalla P04 (Confirmación) la consulta que usaría el frontend es `order(id)` con `createdAt`, `subtotal`, `discount`, `total`, `client { name phone }` e `items { qty name unitPrice discount }` (caso F5 y prueba `test_p04_confirmacion_con_una_sola_consulta_graphql`). El aislamiento de red se demuestra en `docker-compose.yml` (red `private` con `internal: true`; solo el gateway publica el puerto 8000 en `127.0.0.1`) y a nivel de aplicación con las pruebas de acceso directo (403).

# Módulo 9 — Analítica y comunicación gRPC

## 9.1 Matriz de necesidades

""")
b = BENCH
w(tabla(["Necesidad", "Medición o proyección", "Valor", "¿Exige gRPC o analítica?"], [
    ["Volumen real previsto del local", "Proyección (estimación del equipo, sin datos reales)", "≈ 150–300 pedidos/día ≈ 0,5–1 mil hechos/día ≈ 180–360 mil al año", "No: una consulta SQL sobre `orders` lo resuelve"],
    ["Carga sintética de prueba", "Medición", f"{b['rows']:,} hechos de venta".replace(",", "."), "Sirve para comparar mecanismos, no representa el volumen actual"],
    ["Reporte de ventas del dueño", "Requisito R11", "Pocas consultas por día, latencia de segundos aceptable", "No exige gRPC; sí conviene separarlo de las transacciones"],
    ["Exportación masiva / casi tiempo real a consumidores internos", "Escenario de crecimiento (varios locales, delivery)", "Cientos de miles de filas por exportación", "Sí, según la medición: gRPC con streaming por lotes"],
    ["Streaming hacia el navegador", "Requisito", "No hay pantalla que lo pida", "No se implementa; si se necesitara, se adaptaría con SSE/WebSocket desde el GraphQL Gateway sin exponer gRPC"],
]))
w(f"""
## 9.2 ADR-001: servicio de analítica separado y gRPC solo para la entrega masiva

**Contexto.** El caso necesita un resumen de ventas para el dueño y, a futuro, alimentar reportes e integraciones. Con el volumen previsto un reporte pequeño no requiere big data. La guía exige decidir con una caracterización de carga reproducible.

**Alternativas.** (A) Consulta SQL directa en `orders` expuesta por REST. (B) Servicio de analítica privado con REST/JSON. (C) Servicio de analítica privado con gRPC. (D) Broker de mensajería con procesamiento en streaming (por ejemplo Kafka): descartada por costo operativo desproporcionado para el volumen.

**Decisión.** Se implementa un **servicio de analítica privado separado de las transacciones** (C), alimentado por sincronización incremental desde `orders` (cursor por evento «paid», `INSERT OR IGNORE`, retraso aceptado de 60 s), y se usa **gRPC** para sus tres operaciones. La justificación de gRPC se apoya en la medición de la entrega masiva, no en el volumen actual; para el resumen unitario la medición no muestra ventaja. Los datos personales no entran en analítica: solo pedido, producto, cantidad, monto y fecha.

**Consecuencias.** (+) Contrato tipado `.proto`, streaming reanudable y menor costo de CPU y bytes en exportaciones grandes. (+) Las consultas pesadas no compiten con las transacciones. (−) Un servicio y una base más que operar y un retraso de hasta 60 s en los reportes. (−) El resumen unitario podría ser REST sin pérdida medible. (−) El canal gRPC va sin TLS dentro de la red privada: se recomienda mTLS en producción.

## 9.3 Medición de carga (reproducible)

Comando: `python -m bench.load_test 100000` (resultados en `bench/results.json`). Servidores (Vault de desarrollo, gRPC y baseline REST) en un proceso aparte; cliente en otro; bucle local. Entorno: {b['environment']['cpus']} CPU, {b['environment']['ram_mb']} MB de RAM, Python {b['environment']['python']}, grpcio {b['environment']['grpcio']}. Es una **medición** sobre datos sintéticos de {b['rows']:,} filas, no una proyección.

""".replace(",", "."))
e = b["export"]
w("**Exportación completa (mediana de 3 corridas, 0 errores):**\n\n")
w(tabla(["Mecanismo", "Filas", "Bytes en el cable", "Tiempo (s)", "Filas/s", "CPU del servidor (s)"], [
    ["REST/JSON paginado (2000 por página)", e["rest"]["rows"], f"{e['rest']['bytes']:,}".replace(",", "."), e["rest"]["seconds_median"], f"{e['rest']['rows_per_second']:,}".replace(",", "."), e["rest"]["server_cpu_seconds_median"]],
    ["gRPC streaming (lotes de 2000)", e["grpc"]["rows"], f"{e['grpc']['bytes']:,}".replace(",", "."), e["grpc"]["seconds_median"], f"{e['grpc']['rows_per_second']:,}".replace(",", "."), e["grpc"]["server_cpu_seconds_median"]],
]))
w(f"\ngRPC transfiere {e['bytes_ratio_grpc_vs_rest']:.2f} veces los bytes de REST y es {e['speedup_grpc_vs_rest']} veces más rápido, con menor CPU del servidor. Memoria residente máxima del servidor: {b['server_rss_mb_max']} MB.\n\n")
w("**Resumen de ventas (consulta agregada sobre 100.000 filas), con 20 solicitudes por trabajador:**\n\n")
rows = []
for i, wk in enumerate((1, 8, 32)):
    r, g = b["summary"]["rest"][i], b["summary"]["grpc"][i]
    rows.append([wk, f"{r['rps']} / {g['rps']}", f"{r['p50_ms']} / {g['p50_ms']}", f"{r['p95_ms']} / {g['p95_ms']}"])
w(tabla(["Concurrencia", "Solicitudes/s (REST / gRPC)", "p50 ms (REST / gRPC)", "p95 ms (REST / gRPC)"], rows))
w("\nEn la consulta unitaria **no hay diferencia relevante**: el tiempo lo domina el recorrido SQL de las 100.000 filas (≈ 28 solicitudes/s con concurrencia), no el protocolo. Hallazgo de ingeniería: una primera versión enviaba un mensaje gRPC por fila y resultó más lenta que REST (≈ 5.500 filas/s, medida sobre un banco con cliente y servidor en el mismo proceso, por lo que no es una comparación aislada); se rediseñó a lotes de 2000 filas por mensaje y el cliente se movió a un proceso aparte. Los resultados de arriba corresponden al diseño final.\n\n")
w("**Referencia del camino transaccional** (`GET /products` por el gateway completo, mismo proceso, sin objetivo de rendimiento declarado):\n\n")
rows = [[c["workers"], c["rps"], c["p50_ms"], c["p95_ms"]] for c in b["crud_products_via_gateway"]]
w(tabla(["Concurrencia", "Solicitudes/s", "p50 ms", "p95 ms"], rows))
w("""
Objetivos declarados: exportar 100.000 hechos en menos de 2 s (cumplido: ver tabla) y resumir sin errores bajo 32 clientes simultáneos (cumplido, 0 errores). No se declaran objetivos de latencia para el camino transaccional porque el volumen previsto es muy inferior a lo medido.

## 9.4 Implementación y pruebas

* Contrato: `services/analytics/analytics.proto`; servidor `server.py` (interceptor de autenticación por método: llamador, secreto de arista y rol admin); cliente asíncrono `client.py` (metadatos con identidad y `request-id`, plazos).
* **Idempotencia y recuperación:** `Sync` usa un cursor persistente y `INSERT OR IGNORE` (dos sincronizaciones seguidas importan 0). `StreamSales` acepta `after_id` y `limit`, por lo que una desconexión se recupera reanudando desde el último `last_id` sin duplicar; el servidor deja de producir si el cliente cancela (`context.is_active()`) y envía lotes acotados (2000) para limitar memoria.
* **Operaciones largas:** la sincronización completa es corta a este volumen y se resuelve en una RPC con plazo; si creciera, correspondería un trabajo asíncrono con identificador.
* **Pruebas:** """ + prueba("test_sin_credenciales_o_sin_rol_admin_se_rechaza", "test_sync_es_idempotente_y_resumen_correcto", "test_ordenes_no_pagadas_no_cuentan", "test_streaming_entrega_todo_en_orden", "test_resumen_de_ventas_via_graphql_solo_admin", "test_analytics_caido_es_error_parcial_en_graphql", "test_sincronizacion_periodica_automatica") + """.
* Evidencia G9/G10: """ + f"`syncAnalytics` → {ev('G9')['data']['syncAnalytics']} hechos; `salesSummary` → " + json.dumps(ev('G10')['data']['salesSummary'], ensure_ascii=False) + """.

# Módulo 10 — Backend completo e integración verificable

## 10.1 Qué se entrega

* **Código:** `common/` (base compartida), `services/{auth,inventory,clients,orders,payments,analytics,graphql_gateway,api_gateway}`, `scripts/`, `tools/dev_vault.py` (Vault de desarrollo solo para pruebas), `tests/`, `bench/`, `docs/`.
* **Persistencia real:** una base SQLite por servicio (archivo en volumen), con esquema en `schema.sql` (tipos, claves foráneas, `CHECK` de estados y de stock), datos de prueba ficticios sembrados al iniciar con `SEED=1` y marca de siembra para no repetirla. Se eligió SQLite porque no requiere credenciales ni servidor adicional y el esquema es SQL estándar; cambiar de motor solo afectaría a `common/db.py` y a los `schema.sql`. Los servicios no tienen respuestas fijas ni estado en memoria: al reiniciarlos los datos persisten (prueba `test_persistencia_real_sobrevive_al_reinicio`).
* **Despliegue reproducible:** `docker-compose.yml` con redes `public` y `private` (`internal: true`), Vault con política y token por servicio (volumen de solo lectura por servicio), `vault-bootstrap` que genera todos los secretos al arrancar, health checks, `.env.example` sin valores reales y dependencias fijadas en `requirements.txt`.
* **Registros:** JSON con `ts`, `level`, `service`, `request_id`, `event`; el mismo `request_id` recorre todos los servicios; las claves con nombres sensibles se enmascaran automáticamente.

## 10.2 Instrucciones

El docente confirmó que basta con ejecutar en local; Docker es opcional siempre que se entregue el `docker-compose.yml` para replicar.

**Local (forma principal):**

```bash
pip install -r requirements-dev.txt
python -m scripts.run_local      # gateway en http://127.0.0.1:8000, Vault de desarrollo en memoria; Ctrl+C detiene
python -m pytest tests -q        # %d pruebas, sin Docker ni red
python docs/evidencia/mutaciones.py  # verifica que las pruebas detectan fallas introducidas
GATEWAY_URL=... VAULT_ADDR=... VAULT_ROOT_TOKEN=... DEMO_PASSWORD=... python scripts/smoke_e2e.py
python -m bench.load_test 100000 # prueba de carga
python docs/evidencia/capturar.py  # regenera la evidencia del informe
python docs/diagramas/generar.py   # regenera diagramas (PNG, SVG y .drawio)
```

**Docker (opcional):**

```bash
cp .env.example .env             # VAULT_ROOT_TOKEN y DEMO_PASSWORD con valores propios
docker compose up --build        # Vault, generación de secretos y servicios; solo el gateway publica 127.0.0.1:8000
docker compose ps                # health checks
docker compose down -v           # detiene y borra datos y tokens
```

Datos de prueba sembrados (ficticios): los 12 platillos del frontend con sus mismos ids, nombres, categorías y precios (por ejemplo 1 Tacos al Pastor, 4 Burrito Especial, 7 Nachos Supreme, 9 Agua de Horchata, 11 Quesadilla Mixta), la promoción 2x1 en Tacos al Pastor, los clientes CLI-001 y CLI-002 y los usuarios `camila` y `matias` (customer), `cocina` (kitchen), `benjamin` (customer y admin); todos con la clave definida en `DEMO_PASSWORD`. Para configurar referencias de secretos: no se editan valores; el bootstrap crea las rutas `mariachi/edges/<destino>/<llamador>` y `mariachi/payments`. Rotación: `python scripts/vault_bootstrap.py --token-dir /tokens --rotate-edge <llamador> <destino>`.

## 10.3 Matriz requisito · pantalla · servicio · prueba · resultado · evidencia

El resultado se calcula leyendo `docs/evidencia/pytest.xml` (✔ = pasó en la corrida del informe).

""" % TOTAL)
M = [
    ["R01/R02", "P02", "S04, S05", ["test_catalogo_publico_para_visitantes_solo_campos_publicos", "test_p02_menu_filtra_por_categoria_incluida_otros", "test_catalogo_para_cliente_no_expone_cantidades", "test_catalogo_coincide_con_los_datos_del_frontend"], "V1, F1"],
    ["R01 (promoción)", "P01", "S34, S35, S15", ["test_p01_promocion_del_dia_se_aplica_en_el_servidor"], "F2, V4a"],
    ["R03", "P03", "S15", ["test_orden_reserva_stock_y_calcula_total_en_servidor", "test_p03_notas_del_pedido_se_guardan_y_se_limitan_a_200", "test_p03_carrito_vacio_o_cantidades_invalidas_se_rechazan", "test_el_total_nunca_viene_del_navegador"], "V4a"],
    ["R03 (consistencia)", "P03", "S15 + inventory", ["test_no_se_puede_vender_mas_de_lo_que_hay", "test_concurrencia_no_genera_sobreventa", "test_idempotencia_al_crear_orden", "test_orden_no_se_crea_si_inventario_esta_caido", "test_orden_no_se_crea_si_clientes_esta_caido"], "S1"],
    ["R04", "P03", "S12, S14, S01", ["test_p03_formulario_del_frontend_valida_contacto_en_el_servidor", "test_registro_normaliza_el_telefono_como_el_frontend", "test_registro_login_y_primer_pedido", "test_usuario_y_correo_duplicados", "test_correo_duplicado_no_deja_usuario_huerfano", "test_registro_valida_entrada"], "F3, F4"],
    ["R05", "P04", "S30, S17", ["test_p04_confirmacion_con_una_sola_consulta_graphql", "test_agrega_ordenes_inventario_clientes_y_pagos"], "F5, G1"],
    ["R06", "P08", "S22, S23, S24", ["test_pago_exitoso_marca_la_orden_pagada", "test_webhook_duplicado_no_paga_dos_veces", "test_webhooks_duplicados_en_paralelo", "test_crear_pago_dos_veces_devuelve_el_mismo", "test_firma_invalida_o_ausente", "test_monto_distinto_es_rechazado", "test_orders_valida_el_monto_aunque_el_aviso_venga_de_payments", "test_pago_tardio_sobre_orden_expirada_requiere_reembolso", "test_webhook_con_ordenes_caido_se_recupera_con_reintento"], "V6, V7"],
    ["R07", "P06", "S01–S03, S33", ["test_login_cookie_httponly_y_token_fuera_del_cuerpo", "test_credenciales_incorrectas_mismo_mensaje", "test_logout_revoca_la_sesion", "test_sesion_expirada_401", "test_bloqueo_de_cuenta_tras_intentos_fallidos", "test_clave_registrada_se_guarda_con_hash"], "—"],
    ["R08", "P07", "S16–S18", ["test_propiedad_de_ordenes_entre_clientes", "test_cancelar_libera_el_stock", "test_paginacion_de_ordenes"], "V4b, V4c"],
    ["R09", "P09", "S16, S19", ["test_flujo_de_estados_y_commit_de_stock", "test_orden_pendiente_no_puede_prepararse", "test_cliente_no_cancela_orden_pagada_pero_admin_si"], "—"],
    ["R10", "P10", "S06–S10, S20, S21", ["test_matriz_de_permisos_http", "test_ajuste_de_stock_no_baja_de_lo_reservado", "test_expirar_ordenes_pendientes_recupera_stock", "test_recuperacion_de_stock_si_inventario_cae_al_cancelar"], "—"],
    ["R11", "P10", "S27–S32", ["test_sync_es_idempotente_y_resumen_correcto", "test_streaming_entrega_todo_en_orden", "test_resumen_de_ventas_via_graphql_solo_admin", "test_sincronizacion_periodica_automatica"], "G9, G10"],
    ["Seguridad: acceso directo", "—", "todos", ["test_servicios_privados_rechazan_llamadas_sin_credencial", "test_token_de_otra_arista_no_sirve", "test_llamador_fuera_de_la_topologia_es_rechazado", "test_cliente_no_puede_inyectar_identidad_ni_roles"], "V5"],
    ["Seguridad: secretos", "—", "Vault", ["test_vault_minimo_privilegio_por_servicio", "test_secretos_distintos_por_integracion", "test_rotacion_con_gracia_y_revocacion", "test_rotacion_del_secreto_del_webhook", "test_vault_caido_falla_cerrado", "test_los_logs_no_contienen_secretos", "test_contrasenas_y_sesiones_no_se_guardan_en_claro"], "L2"],
    ["GraphQL: límites", "—", "S30", ["test_limite_de_profundidad", "test_limite_de_costo_rechaza_consultas_abusivas", "test_limites_de_pagina_y_cursor_invalido", "test_introspeccion_deshabilitada_y_get_no_permitido", "test_batching_evita_n_mas_1"], "G4–G6, G1b"],
    ["GraphQL: autorización y fallos", "—", "S30", ["test_autorizacion_por_campo", "test_correo_del_cliente_solo_para_dueno_o_admin", "test_no_se_ve_la_orden_de_otro_cliente", "test_errores_parciales_si_clientes_no_responde", "test_errores_parciales_si_inventario_no_responde", "test_analytics_caido_es_error_parcial_en_graphql"], "G2, G3, G7, V4d"],
    ["Límites del gateway", "—", "api-gateway", ["test_limite_de_tasa_en_login_del_gateway", "test_limite_de_tasa_general_del_gateway", "test_registro_con_limite_de_tasa", "test_cuerpo_no_json_y_cuerpo_grande", "test_gateway_corta_antes_de_llamar_al_servicio", "test_rutas_internas_no_salen_por_el_gateway"], "V3"],
    ["Operación", "—", "todos", ["test_health_y_ready_de_todos_los_servicios", "test_un_mismo_request_id_recorre_todos_los_servicios", "test_logs_estructurados_con_campos_minimos", "test_persistencia_real_sobrevive_al_reinicio", "test_siembra_y_esquema_son_reproducibles", "test_restricciones_de_base_de_datos_impiden_datos_invalidos", "test_cada_servicio_publica_su_contrato_openapi"], "H1, L1"],
]
filas = []
for req, pant, serv, tests, evid in M:
    ok = all(RESULT.get(t) for t in tests)
    filas.append([req, pant, serv, "; ".join(f"`{t}`" for t in tests), f"✔ {len(tests)}/{len(tests)}" if ok else "✘ revisar", evid])
w(tabla(["Requisito", "Pantalla", "Servicio", "Pruebas", "Resultado", "Evidencia"], filas))
w(f"""
Resultado global de la corrida del informe: **{TOTAL} pruebas, {FALLAS} fallas** en {TIME:.0f} s. Además, el recorrido de extremo a extremo `scripts/smoke_e2e.py`, ejecutado contra el sistema levantado con `scripts/run_local.py`, dio {SMOKE[-1].strip()} (registro en `docs/evidencia/smoke_e2e.txt`).

Las pruebas son de contratos, integración, reglas de negocio y seguridad contra servicios reales levantados (con Vault de desarrollo y bases SQLite temporales). Para comprobar que **detectan defectos** se ejecutó `docs/evidencia/mutaciones.py`: introduce una falla a propósito en una copia del código, corre la prueba que debería detectarla y deshace el cambio. Resultado (`docs/evidencia/mutaciones.json`):

""")
w(tabla(["Falla introducida", "Archivo", "Prueba", "Sin la falla", "Con la falla"], [[m["mutante"], f"`{m['archivo']}`", f"`{m['prueba']}`", m["sin_mutar"], m["con_mutacion"]] for m in MUT]))
w(f"""
{sum(1 for m in MUT if m["con_mutacion"].startswith("falla"))} de {len(MUT)} fallas fueron detectadas. En una primera corrida la falla M6 (quitar en `orders` la comparación del monto) no se detectaba, porque `payments` ya rechaza el monto alterado antes; se agregó la prueba `test_orders_valida_el_monto_aunque_el_aviso_venga_de_payments`, que llama a `orders` con la identidad de `payments` y un monto distinto.

## 10.4 Demostración con datos del frontend

Siguiendo la instrucción docente, cada servicio se ejecuta con los datos que maneja el frontend (`script.js` de la carpeta `evaluacion1_frontend`), a través del API Gateway. El arreglo `menu` del frontend está copiado en la prueba `test_catalogo_coincide_con_los_datos_del_frontend`.

""")
w(tabla(["Caso", "Pantalla y dato del frontend", "Solicitud", "Estado", "Resultado"], [
    ["F1", "P02 · arreglo `menu` (ids 1–12)", EV["F1"]["solicitud"], EV["F1"]["estado"], "; ".join(f"{p['id']} {p['name']} {p['category']} ${p['price']}" for p in ev("F1")["items"])],
    ["F2", "P01 · banner «PROMOCIÓN DEL DÍA: 2x1 en Tacos al Pastor»", EV["F2"]["solicitud"], EV["F2"]["estado"], ev("F2")["items"][0]["label"]],
    ["F3", "P03 · campos `nombreCliente`, `telefonoCliente`, `emailCliente`", EV["F3"]["solicitud"], EV["F3"]["estado"], f"nombre «{ev('F3')['name']}», teléfono {ev('F3')['phone']}"],
    ["F4", "P03 · `validarTelefono` rechaza `12345`", EV["F4"]["solicitud"], EV["F4"]["estado"], ev("F4")["error"]["details"][0]["msg"]],
    ["V4a", "P03 · carrito 2× Tacos al Pastor + 1× Quesadilla Mixta y notas", EV["V4a"]["solicitud"], EV["V4a"]["estado"], f"{ev('V4a')['id']}: subtotal {ev('V4a')['subtotal']}, descuento {ev('V4a')['discount']}, total {ev('V4a')['total']}"],
    ["F5", "P04 · número, fecha, cliente, teléfono, ítems y total", "GraphQL `order(id)`", EV["F5"]["estado"], f"{ev('F5')['data']['order']['client']['name']}, {ev('F5')['data']['order']['client']['phone']}, total {ev('F5')['data']['order']['total']}"],
]))
w("""
**Consulta protegida autorizada y denegada** (misma regla de propiedad en `orders`): Camila consulta su pedido (V4b, `200`) y Matías el mismo pedido (V4c, `404` sin datos):

""")
w(jbloque({"V4b_camila": {"estado": EV["V4b"]["estado"], "id": ev("V4b")["id"], "total": ev("V4b")["total"]}, "V4c_matias": {"estado": EV["V4c"]["estado"], "respuesta": ev("V4c")}}))
w("""
## 10.5 Evidencias adicionales

**Readiness de cada servicio (H1):**

""")
w(jbloque(ev("H1", "resultado"), 900))
w("\n**Trazabilidad con un mismo `request_id` (L1)** — un único `POST /orders` deja estas líneas en cinco servicios:\n\n")
w(tabla(["Servicio", "Evento", "Detalle"], [[l["service"], l["event"], " ".join(str(l.get(k, "")) for k in ("method", "path", "status", "callee")).strip()] for l in EV["L1"]["lineas"]]))
w(f"\n**Secretos en logs (L2):** se buscaron {EV['L2']['secretos_buscados']} secretos reales (tokens de Vault, secreto del webhook, cookie de sesión) en {EV['L2']['lineas_revisadas']} líneas de log: {EV['L2']['coincidencias']} coincidencias.\n\n")
w("**Sobreventa bajo concurrencia (S1):** " + str(ev("S1", "resultado")) + " — con stock de 30 y compras de 5 unidades, exactamente 6 pedidos pasan.\n\n")

w("""# Limitaciones y trabajo pendiente (declaradas)

* **Docker es opcional** (confirmado por el docente: basta con local). La demostración principal es local. El `docker-compose.yml` se entrega para replicar; su sintaxis se validó con `docker compose config`, pero en el entorno donde se desarrolló no se pudo ejecutar (sin acceso a las imágenes). En local, la separación pública/privada se demuestra porque cada servicio privado rechaza con 403 las llamadas sin el secreto de su integración; con Docker se suma el aislamiento de red.
* **Vault real:** el compose usa el modo de desarrollo (memoria, sin TLS ni sellado). En producción: modo servidor con almacenamiento persistente, TLS, AppRole o identidad de plataforma y tokens renovables.
* **TLS/mTLS:** no configurado dentro de la red privada; el TLS público se delega a un proxy delante del gateway. gRPC va sin cifrar en la red privada.
* **Frontend no integrado** por instrucción del docente (se evidencia con sus datos, módulo 10.4); brechas B2–B4 (pantallas faltantes, número de orden generado en el navegador, boletas y mensajería). B1 (promoción) quedó resuelta en el backend.
* **Proveedor de pagos:** adaptador de prueba que firma eventos con el mismo contrato; no se integró un entorno de pruebas real.
* **Eliminación/anonimización de cuentas** no implementada (procedimiento propuesto en 7.3).
* **Límite de tasa en memoria** por instancia del gateway; con varias instancias debería ser compartido.
* **Sin circuit breaker**: solo plazos y un reintento en GET.
* **Usuarios pendientes de registro:** si un proceso muere entre crear el usuario pendiente y el perfil, queda una fila inactiva que bloquea ese nombre; se limpiaría con una tarea de mantenimiento (no implementada).
* **Número del caso** en el listado de 40 casos: pendiente de completar en la portada.
""")

out = ROOT / "docs/INFORME.md"
out.write_text("\n".join(md))
print("informe", len("\n".join(md)), "caracteres")
