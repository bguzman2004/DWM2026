import json
import sys
import tempfile
import threading
import uuid
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.support.helpers import ADMIN, gql, items_payload, place_order, start_payment, webhook
from tests.support.stack import Stack

OUT = Path(__file__).parent
registro = []


def anotar(clave, titulo, solicitud, respuesta, verifica):
    try:
        cuerpo = respuesta.json()
    except Exception:
        cuerpo = respuesta.text
    registro.append(
        {
            "id": clave,
            "titulo": titulo,
            "solicitud": solicitud,
            "estado": respuesta.status_code,
            "respuesta": cuerpo,
            "request_id": respuesta.headers.get("x-request-id"),
            "verifica": verifica,
        }
    )
    return respuesta


def main():
    stack = Stack(Path(tempfile.mkdtemp()), extra={"api-gateway": {"limits": {"login": (1000, 60), "default": (100000, 60)}}}).start()
    try:
        gw = stack.urls["api-gateway"]
        anon = httpx.Client(base_url=gw, timeout=15)
        anotar("V1", "Acceso anonimo al catalogo", "GET /products (sin sesion)", anon.get("/products", params={"category": "Otros"}), "gateway: ruta publica; inventory: solo campos publicos")
        anotar("V2", "Operacion protegida sin sesion", "GET /orders (sin cookie)", anon.get("/orders"), "api-gateway: introspeccion exige sesion")
        camila, matias, admin, cocina = (stack.client(u) for u in ("camila", "matias", "benjamin", "cocina"))
        anotar("F1", "P02 Menu: los platillos del frontend existen con el mismo id, nombre, categoria y precio", "GET /products?limit=12 (sin sesion)", anon.get("/products", params={"limit": 12}), "inventory: catalogo coherente con script.js del frontend")
        anotar("F2", "P01 Inicio: promocion del dia publicada por el backend", "GET /promotions (sin sesion)", anon.get("/promotions"), "inventory: promocion vigente; el banner deja de ser texto fijo")
        anotar("F3", "P03 Pedido: datos de contacto del formulario", 'PATCH /clients/CLI-001 {name: "  Camila   Rojas ", phone: "9 1111 1111", email: "camila.rojas@example.com"} (camila)', camila.patch("/clients/CLI-001", json={"name": "  Camila   Rojas ", "phone": "9 1111 1111", "email": "camila.rojas@example.com"}), "clients: valida y normaliza como el formulario (celular chileno, nombre >= 3)")
        anotar("F4", "P03 Pedido: telefono invalido segun la regla del frontend", 'PATCH /clients/CLI-001 {phone: "12345"} (camila)', camila.patch("/clients/CLI-001", json={"phone": "12345"}), "clients: el servidor repite la validacion del navegador")
        anotar("V3", "Administracion desde rol sin permiso", "POST /products con sesion de camila (customer)", camila.post("/products", json={"name": "Hack", "category": "Tacos", "price": 100}), "api-gateway (rol) y inventory (rol) - doble verificacion")
        orden = camila.post("/orders", json={**items_payload([(1, 2), (11, 1)]), "notes": "sin cebolla"})
        anotar("V4a", "Cliente crea orden; el total lo calcula el servidor", "POST /orders {items:[{product_id:1, qty:2},{product_id:11, qty:1}], notes} (carrito de P03)", orden, "orders + inventory (reserva, precio y 2x1 calculados en el servidor)")
        anotar("F5", "P04 Confirmacion: datos que muestra la pantalla en una consulta", "query order(id) { id createdAt subtotal discount total notes client { name phone } items { qty name unitPrice discount } }", gql(camila, 'query($id: String!) { order(id: $id) { id createdAt subtotal discount total notes client { name phone } items { qty name unitPrice discount promo } } }', {"id": orden.json()["id"]}), "graphql-gateway: orders + clients")
        oid = orden.json()["id"]
        anotar("V4b", "Consulta de pedido propio", f"GET /orders/{oid} (camila)", camila.get(f"/orders/{oid}"), "orders: propiedad del recurso")
        anotar("V4c", "Consulta de pedido ajeno", f"GET /orders/{oid} (matias)", matias.get(f"/orders/{oid}"), "orders: propiedad; responde 404 para no revelar existencia")
        anotar("V4d", "Pedido ajeno por GraphQL", "query { order(id) { id total } } (matias)", gql(matias, f'{{ order(id: "{oid}") {{ id total }} }}'), "graphql-gateway delega en orders; devuelve null")
        token_otra_arista = stack.root.read("mariachi/edges/inventory/orders")["token"]
        anotar("V5a", "Acceso directo al backend sin identidad", "GET orders:/orders (sin cabeceras de servicio)", httpx.get(f"{stack.urls['orders']}/orders"), "orders: garantia de llamador")
        anotar("V5b", "Acceso directo con secreto de otra arista", "GET inventory:/products con token orders->inventory declarando ser graphql-gateway", httpx.get(f"{stack.urls['inventory']}/products", headers={"X-Service-Caller": "graphql-gateway", "X-Service-Token": token_otra_arista}), "inventory: secreto por arista")
        anotar("V5c", "Cliente inyecta cabeceras de identidad", "POST /products con X-Roles: admin (camila)", camila.post("/products", json={"name": "Hack", "category": "Tacos", "price": 100}, headers={"X-Roles": "admin", "X-User-Id": "USR-004"}), "api-gateway descarta cabeceras de identidad del navegador")
        pago = start_payment(camila, oid, key="clave-evidencia-0001")
        anotar("V6a", "Inicio de pago", "POST /payments {order_id} + Idempotency-Key", pago, "payments: monto tomado de orders")
        ref, monto = pago.json()["provider_ref"], pago.json()["amount"]
        anotar("V6b", "Confirmar pago sin firma valida (datos alterados)", "POST /payments/webhook firma incorrecta", webhook(stack, ref, monto, secret="firma-falsa"), "payments: HMAC con secreto de Vault")
        anotar("V6c", "Confirmar pago con monto alterado", "POST /payments/webhook monto-1 con firma valida", webhook(stack, ref, monto - 1), "payments: compara con el monto guardado")
        anotar("V6d", "Cliente intenta marcar pagado desde el navegador", f"PATCH /orders/{oid}/status {{status: preparando}} (camila)", camila.patch(f"/orders/{oid}/status", json={"status": "preparando"}), "api-gateway y orders: solo cocina/admin")
        anotar("V6e", "Cliente intenta llamar la ruta interna de pago", f"POST /internal/orders/{oid}/paid (camila)", camila.post(f"/internal/orders/{oid}/paid", json={"payment_id": "PAY-X", "amount": monto}), "api-gateway: ruta no publicada")
        evento = "evt_evidencia_01"
        anotar("V7a", "Webhook valido", "POST /payments/webhook firmado", webhook(stack, ref, monto, event_id=evento), "payments -> orders (paid)")
        anotar("V7b", "Webhook duplicado", "POST /payments/webhook mismo event_id", webhook(stack, ref, monto, event_id=evento), "payments: webhook_events.event_id unico")
        anotar("V7c", "Estado final de la orden", f"GET /orders/{oid}", camila.get(f"/orders/{oid}"), "orders: una sola transicion a pagado")

        consulta = (
            "{ myOrders(first: 10) { total nextCursor nodes { id status subtotal discount total notes "
            "client { id name email } items { name qty unitPrice discount product { name category inStock } } "
            "payment { status amount } } } }"
        )
        anotar("G1", "Agregacion GraphQL (orders+inventory+clients+payments)", "POST /graphql myOrders(first:10)", gql(camila, consulta), "graphql-gateway: 4 subsistemas, 4 llamadas por lote")
        stack.call_log.clear()
        gql(camila, consulta)
        llamadas = [list(c) for c in stack.call_log]
        registro.append({"id": "G1b", "titulo": "Llamadas internas de la agregacion (batching)", "llamadas": llamadas})
        anotar("G2", "Campo restringido por rol", "product(id:1){ stock{available} } (camila)", gql(camila, "{ product(id: 1) { name stock { available } } }"), "campo stock: permiso de staff")
        anotar("G3", "Mismo campo con rol cocina", "product(id:1){ stock{available} } (cocina)", gql(cocina, "{ product(id: 1) { name stock { available } } }"), "campo stock: staff")
        base = "myOrders(first: 50) { nodes { items { product { name } } client { name } } }"
        anotar("G4", "Limite de costo", "6 alias de myOrders(first:50)", gql(camila, "{ " + " ".join(f"q{i}: {base}" for i in range(6)) + " }"), "validacion previa a ejecutar")
        anotar("G5", "Limite de pagina", "products(first: 51)", gql(camila, "{ products(first: 51) { total } }"), "resolver")
        anotar("G6", "Introspeccion deshabilitada", "{ __schema { types { name } } }", gql(camila, "{ __schema { types { name } } }"), "regla de validacion")
        stack.stop_service("clients")
        try:
            anotar("G7", "Error parcial: clients caido", "myOrders { nodes { id total client { name } items { name } } }", gql(camila, "{ myOrders(first: 5) { nodes { id total client { name } items { name } } } }"), "datos de orders se conservan; client=null con error")
        finally:
            stack.start_service("clients")
        anotar("G8", "Resumen de ventas (cliente)", "salesSummary (camila)", gql(camila, "{ salesSummary { orders revenue } }"), "resolver: solo admin")
        anotar("G9", "Sincronizacion analitica (admin)", "mutation { syncAnalytics }", gql(admin, "mutation { syncAnalytics }"), "graphql -> gRPC Sync -> orders export")
        anotar("G10", "Resumen de ventas (admin) por gRPC", "salesSummary(days:7, top:3)", gql(admin, "{ salesSummary(days: 7, top: 3) { orders revenue topProducts { productId name units revenue } } }"), "gRPC unary SalesSummary con deadline y metadata")

        resultados = []
        otros = [stack.client("camila" if i % 2 else "matias") for i in range(10)]

        def comprar(c):
            resultados.append(place_order(c, [(7, 5)]).status_code)

        hilos = [threading.Thread(target=comprar, args=(c,)) for c in otros]
        [h.start() for h in hilos]
        [h.join() for h in hilos]
        registro.append({"id": "S1", "titulo": "10 compras simultaneas de 5 unidades con stock 30", "resultado": sorted(resultados), "verifica": "inventory: UPDATE condicional atomico; sin sobreventa"})

        health = {n: httpx.get(f"{stack.urls[n]}/ready").json() for n in ("api-gateway", "auth", "inventory", "clients", "orders", "payments", "graphql-gateway")}
        registro.append({"id": "H1", "titulo": "Readiness de cada servicio", "resultado": health})

        rid = orden.headers["x-request-id"]
        eventos = [e for e in stack.capture.events() if e["request_id"] == rid]
        registro.append(
            {
                "id": "L1",
                "titulo": f"Logs con el mismo request_id {rid} en toda la cadena",
                "lineas": [
                    {k: e[k] for k in ("service", "event", "method", "path", "status", "callee", "user", "caller") if k in e}
                    for e in eventos
                ],
            }
        )
        todo = "\n".join(stack.capture.lines)
        secretos = list(stack.tokens.values()) + [stack.root.read("mariachi/payments")["webhook_hmac"], camila.cookies.get("session_token")]
        registro.append({"id": "L2", "titulo": "Busqueda de secretos en los logs", "lineas_revisadas": len(stack.capture.lines), "secretos_buscados": len(secretos), "coincidencias": sum(todo.count(s) for s in secretos)})
    finally:
        stack.stop()
    (OUT / "ejecuciones.json").write_text(json.dumps(registro, indent=2, ensure_ascii=False))
    print(f"{len(registro)} registros")


if __name__ == "__main__":
    main()
