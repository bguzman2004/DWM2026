import html
import json
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape as _escape


def escape(text):
    return _escape(text, {'"': "&quot;"})

OUT = Path(__file__).parent

COLORS = {
    "entity": ("#FFF2CC", "#B8860B"),
    "service": ("#DAE8FC", "#3B6EA8"),
    "policy": ("#E1D5E7", "#7A5C99"),
    "adapter": ("#D5E8D4", "#4F8A3B"),
    "external": ("#F8CECC", "#B85450"),
    "store": ("#F5F5F5", "#666666"),
    "secret": ("#FFE6CC", "#C77700"),
}


class Node:
    def __init__(self, key, name, kind, stereotype=None, attrs=(), ops=(), lines=None, shape="box"):
        self.key, self.name, self.kind, self.stereotype = key, name, kind, stereotype
        self.attrs, self.ops, self.lines, self.shape = list(attrs), list(ops), lines, shape

    def dot_label(self):
        fill, line = COLORS[self.kind]
        rows = []
        head = ""
        if self.stereotype:
            head += f'<FONT POINT-SIZE="8">«{html.escape(self.stereotype)}»</FONT><BR/>'
        head += f"<B>{html.escape(self.name)}</B>"
        rows.append(f'<TR><TD BGCOLOR="{fill}" ALIGN="CENTER">{head}</TD></TR>')
        if self.lines is not None:
            for text in self.lines:
                rows.append(f'<TR><TD ALIGN="LEFT" BORDER="0"><FONT POINT-SIZE="9">{html.escape(text)}</FONT></TD></TR>')
        else:
            for part in (self.attrs, self.ops):
                if part:
                    body = "".join(f'{html.escape(t)}<BR ALIGN="LEFT"/>' for t in part)
                    rows.append(f'<TR><TD ALIGN="LEFT"><FONT POINT-SIZE="9">{body}</FONT></TD></TR>')
        return f'<<TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="3" COLOR="{line}">{"".join(rows)}</TABLE>>'

    def drawio_value(self):
        head = ""
        if self.stereotype:
            head += f'<span style="font-size:9px">«{escape(self.stereotype)}»</span><br>'
        head += f"<b>{escape(self.name)}</b>"
        body = f'<div style="text-align:center">{head}</div>'
        if self.lines is not None:
            body += "<hr size=\"1\">" + "<br>".join(escape(t) for t in self.lines)
        else:
            for part in (self.attrs, self.ops):
                if part:
                    body += '<hr size="1">' + "<br>".join(escape(t) for t in part)
        return body


class Edge:
    def __init__(self, a, b, kind="assoc", ma="", mb="", label="", constraint=True):
        self.a, self.b, self.kind, self.ma, self.mb, self.label, self.constraint = a, b, kind, ma, mb, label, constraint


class Diagram:
    def __init__(self, name, title, rankdir="TB", clusters=None):
        self.name, self.title, self.rankdir = name, title, rankdir
        self.nodes, self.edges, self.clusters = {}, [], clusters or {}

    def node(self, *args, cluster=None, **kw):
        n = Node(*args, **kw)
        n.cluster = cluster
        self.nodes[n.key] = n
        return n

    def edge(self, *args, **kw):
        self.edges.append(Edge(*args, **kw))

    def dot(self):
        out = [f'digraph "{self.name}" {{', f'rankdir={self.rankdir}; nodesep=0.55; ranksep=0.7; splines=true; compound=true;',
               'node [shape=plaintext fontname="Helvetica" fontsize=10]; edge [fontname="Helvetica" fontsize=9 labeldistance=1.6];']
        grouped = {}
        for n in self.nodes.values():
            grouped.setdefault(n.cluster, []).append(n)
        for key, members in grouped.items():
            if key:
                title = self.clusters[key]
                out.append(f'subgraph cluster_{key} {{ label="{title}"; style="rounded,dashed"; color="#888888"; fontname="Helvetica"; fontsize=10; labeljust=l;')
            for n in members:
                if n.shape == "cylinder":
                    out.append(f'"{n.key}" [shape=cylinder style=filled fillcolor="{COLORS[n.kind][0]}" color="{COLORS[n.kind][1]}" label="{n.name}" fontsize=9];')
                else:
                    out.append(f'"{n.key}" [label={n.dot_label()}];')
            if key:
                out.append("}")
        for e in self.edges:
            attrs = []
            if e.label:
                attrs.append(f'label="{e.label}"')
            if e.ma:
                attrs.append(f'taillabel="{e.ma}"')
            if e.mb:
                attrs.append(f'headlabel="{e.mb}"')
            if e.kind == "assoc":
                attrs.append("arrowhead=none")
            elif e.kind == "comp":
                attrs += ["dir=both", "arrowtail=diamond", "arrowhead=none"]
            elif e.kind == "agg":
                attrs += ["dir=both", "arrowtail=odiamond", "arrowhead=none"]
            elif e.kind == "dep":
                attrs += ["style=dashed", "arrowhead=vee"]
            elif e.kind == "flow":
                attrs += ["arrowhead=normal"]
            elif e.kind == "secret":
                attrs += ["style=dotted", "color=\"#C77700\"", "fontcolor=\"#C77700\"", "arrowhead=vee"]
            elif e.kind == "grpc":
                attrs += ["color=\"#4F8A3B\"", "fontcolor=\"#4F8A3B\"", "penwidth=2", "arrowhead=normal"]
            if not e.constraint:
                attrs.append("constraint=false")
            out.append(f'"{e.a}" -> "{e.b}" [{", ".join(attrs)}];')
        out.append("}")
        return "\n".join(out)

    def render(self):
        dot_src = self.dot()
        (OUT / f"{self.name}.dot").write_text(dot_src)
        for fmt in ("png", "svg"):
            args = ["dot", f"-T{fmt}"] + (["-Gdpi=130"] if fmt == "png" else [])
            subprocess.run(args + ["-o", str(OUT / f"{self.name}.{fmt}"), str(OUT / f"{self.name}.dot")], check=True)
        layout = json.loads(subprocess.run(["dot", "-Tjson", str(OUT / f"{self.name}.dot")], capture_output=True, text=True, check=True).stdout)
        self.drawio(layout)

    def drawio(self, layout):
        x0, y0, x1, y1 = (float(v) for v in layout["bb"].split(","))
        height = y1 - y0
        cells = ['<mxCell id="0"/>', '<mxCell id="1" parent="0"/>']
        ids = {}
        counter = [2]

        def new_id():
            counter[0] += 1
            return f"c{counter[0]}"

        for obj in layout.get("objects", []):
            if obj["name"].startswith("cluster_"):
                bx0, by0, bx1, by1 = (float(v) for v in obj["bb"].split(","))
                cid = new_id()
                title = self.clusters[obj["name"][len("cluster_"):]]
                cells.append(
                    f'<mxCell id="{cid}" value="{escape(title)}" style="rounded=1;dashed=1;fillColor=none;strokeColor=#888888;verticalAlign=top;align=left;spacingLeft=8;fontSize=11;fontStyle=2;" vertex="1" parent="1">'
                    f'<mxGeometry x="{bx0 - x0:.0f}" y="{height - (by1 - y0):.0f}" width="{bx1 - bx0:.0f}" height="{by1 - by0:.0f}" as="geometry"/></mxCell>'
                )
        for obj in layout["objects"]:
            if obj["name"] in self.nodes:
                n = self.nodes[obj["name"]]
                px, py = (float(v) for v in obj["pos"].split(","))
                w = float(obj["width"]) * 72
                h = float(obj["height"]) * 72
                fill, line = COLORS[n.kind]
                cid = new_id()
                ids[n.key] = cid
                if n.shape == "cylinder":
                    style = f"shape=cylinder3;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={line};fontSize=10;"
                    value = escape(n.name)
                else:
                    style = f"rounded=0;whiteSpace=wrap;html=1;align=left;verticalAlign=top;spacingLeft=6;spacingRight=6;fillColor={fill};strokeColor={line};fontSize=10;fontFamily=Helvetica;"
                    value = escape(n.drawio_value())
                cells.append(
                    f'<mxCell id="{cid}" value="{value}" style="{style}" vertex="1" parent="1">'
                    f'<mxGeometry x="{px - x0 - w / 2:.0f}" y="{height - (py - y0) - h / 2:.0f}" width="{w:.0f}" height="{h:.0f}" as="geometry"/></mxCell>'
                )
        for e in self.edges:
            eid = new_id()
            base = "html=1;endArrow=none;endFill=0;fontSize=10;"
            if e.kind == "comp":
                base = "html=1;startArrow=diamondThin;startFill=1;endArrow=none;fontSize=10;"
            elif e.kind == "agg":
                base = "html=1;startArrow=diamondThin;startFill=0;endArrow=none;fontSize=10;"
            elif e.kind == "dep":
                base = "html=1;dashed=1;endArrow=open;endFill=0;fontSize=10;"
            elif e.kind == "flow":
                base = "html=1;endArrow=block;endFill=1;fontSize=10;"
            elif e.kind == "secret":
                base = "html=1;dashed=1;dashPattern=1 3;strokeColor=#C77700;fontColor=#C77700;endArrow=open;fontSize=10;"
            elif e.kind == "grpc":
                base = "html=1;strokeColor=#4F8A3B;fontColor=#4F8A3B;strokeWidth=2;endArrow=block;endFill=1;fontSize=10;"
            cells.append(
                f'<mxCell id="{eid}" value="{escape(e.label)}" style="{base}" edge="1" parent="1" source="{ids[e.a]}" target="{ids[e.b]}">'
                f'<mxGeometry relative="1" as="geometry"/></mxCell>'
            )
            for text, pos in ((e.ma, -0.82), (e.mb, 0.82)):
                if text:
                    cells.append(
                        f'<mxCell id="{new_id()}" value="{escape(text)}" style="edgeLabel;html=1;align=center;verticalAlign=middle;resizable=0;points=[];fontSize=10;" vertex="1" connectable="0" parent="{eid}">'
                        f'<mxGeometry x="{pos}" y="12" relative="1" as="geometry"><mxPoint as="offset"/></mxGeometry></mxCell>'
                    )
        w = int(x1 - x0) + 80
        h = int(height) + 80
        xml = (
            '<mxfile host="app.diagrams.net"><diagram name="' + escape(self.title) + '" id="' + self.name + '">'
            f'<mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{w}" pageHeight="{h}" math="0" shadow="0">'
            "<root>" + "".join(cells) + "</root></mxGraphModel></diagram></mxfile>"
        )
        (OUT / f"{self.name}.drawio").write_text(xml)


def dominio():
    d = Diagram("uml_dominio", "UML dominio y servicios publicos", rankdir="TB", clusters={"clients": "clients", "auth": "auth", "inventory": "inventory", "orders": "orders", "payments": "payments", "analytics": "analytics", "svc": "Servicios publicos (estereotipo service)"})
    d.node("cliente", "Cliente", "entity", attrs=["id: String  «CLI-001»", "nombre: String", "correo: String  «restringido»", "telefono: String  «restringido»", "creado: DateTime"], cluster="clients")
    d.node("usuario", "Usuario", "entity", attrs=["id: String", "username: String", "claveHash: Bytes  «scrypt+sal»", "roles: Set<Rol>", "activo: Boolean"], cluster="auth")
    d.node("sesion", "Sesion", "entity", attrs=["tokenHash: String  «sha256»", "expira: DateTime"], cluster="auth")
    d.node("producto", "Producto", "entity", attrs=["id: Int", "nombre: String", "categoria: Categoria", "precio: Int", "activo: Boolean"], cluster="inventory")
    d.node("stock", "Stock", "entity", attrs=["enMano: Int", "reservado: Int", "«enMano >= reservado >= 0»"], cluster="inventory")
    d.node("promo", "Promocion", "entity", attrs=["id: Int", "tipo: «2x1»", "etiqueta: String", "activa: Boolean"], cluster="inventory")
    d.node("reserva", "Reserva", "entity", attrs=["pedidoId: String", "cantidad: Int", "precioUnitario: Int", "descuento: Int", "estado: reservada|confirmada|liberada"], cluster="inventory")
    d.node("pedido", "Pedido", "entity", attrs=["id: String  «ORD-XXXXXXXX»", "clienteId: String", "estado: EstadoPedido", "subtotal: Int", "descuento: Int", "total: Int  «subtotal - descuento»", "notas: String(<=200)", "stockLiberado: Boolean"], cluster="orders")
    d.node("detalle", "DetallePedido", "entity", attrs=["productoId: Int", "nombre: String  «copia»", "precioUnitario: Int  «copia»", "cantidad: Int(1..20)", "descuento: Int", "promo: String?"], cluster="orders")
    d.node("evped", "EventoPedido", "entity", attrs=["evento: creado|pagado|estado|cancelado|expirado", "fecha: DateTime"], cluster="orders")
    d.node("pago", "Pago", "entity", attrs=["id: String", "pedidoId: String", "monto: Int", "estado: pending|succeeded|failed|requires_refund", "refProveedor: String", "claveIdempotencia: String", "ordenSincronizada: Boolean"], cluster="payments")
    d.node("evweb", "EventoWebhook", "entity", attrs=["eventoId: String  «unico»", "tipo: String", "recibido: DateTime"], cluster="payments")
    d.node("hecho", "HechoVenta", "entity", attrs=["pedidoId: String", "productoId: Int", "cantidad: Int", "monto: Int", "fecha: DateTime"], cluster="analytics")

    d.node("s_auth", "AuthService", "service", "service", ops=["+registrar(RegistroDTO): UsuarioDTO   S01", "+ingresar(Credenciales): SesionDTO   S02", "+salir(): void   S03", "+identidadActual(): IdentidadDTO   S33", "+introspectar(token): IdentidadDTO   (interno)"], cluster="svc")
    d.node("s_cat", "CatalogService", "service", "service", ops=["+consultarCatalogo(filtro): ProductoDTO[]   S04", "+obtenerProducto(id): ProductoDTO   S05", "+crearProducto(ProductoIn): ProductoDTO   S06", "+modificarProducto(id, cambios): ProductoDTO   S07", "+desactivarProducto(id): void   S08", "+consultarStock(): StockDTO[]   S09", "+ajustarStock(id, delta, motivo): StockDTO   S10", "+consultarPromociones(): PromocionDTO[]   S34", "+activarPromocion(id, activa): PromocionDTO   S35", "+reservar / liberar / confirmar   (interno)"], cluster="svc")
    d.node("s_cli", "ClientService", "service", "service", ops=["+listarClientes(): ClienteDTO[]   S11", "+obtenerCliente(id): ClienteDTO   S12", "+crearCliente(ClienteIn): ClienteDTO   S13", "+modificarCliente(id, cambios): ClienteDTO   S14"], cluster="svc")
    d.node("s_ord", "OrderService", "service", "service", ops=["+crearPedido(PedidoIn): PedidoDTO   S15", "+consultarPedidos(filtro): PedidoDTO[]   S16", "+consultarPedido(id): PedidoDTO   S17", "+anularPedido(id): AnulacionDTO   S18", "+avanzarEstado(id, estado): PedidoDTO   S19", "+expirarPendientes(): Id[]   S20", "+conciliarStock(): ResultadoDTO   S21"], cluster="svc")
    d.node("s_pay", "PaymentService", "service", "service", ops=["+iniciarPago(PagoIn): PagoDTO   S22", "+recibirNotificacion(Evento): ResultadoDTO   S23", "+consultarPago(id): PagoDTO   S24", "+listarPagos(filtro): PagoDTO[]   S25", "+conciliarPagos(): ResultadoDTO   S26"], cluster="svc")
    d.node("s_ana", "AnalyticsService", "service", "service gRPC", ops=["+sincronizar(): int   S27", "+resumenVentas(dias, top): ResumenDTO   S28", "+transmitirVentas(desde): stream HechoVentaDTO   S29"], cluster="svc")
    d.node("s_gql", "GraphQLGateway", "adapter", "service", ops=["+myOrders / order / products / product / me   S30", "+createOrder   S31", "+salesSummary / syncAnalytics   S32"], cluster="svc")

    d.edge("cliente", "usuario", "assoc", "1", "0..1", "tiene acceso")
    d.edge("usuario", "sesion", "comp", "1", "0..*", "abre")
    d.edge("cliente", "pedido", "assoc", "1", "0..*", "realiza")
    d.edge("pedido", "detalle", "comp", "1", "1..*", "contiene")
    d.edge("pedido", "evped", "comp", "1", "1..*", "registra")
    d.edge("producto", "stock", "comp", "1", "1", "tiene")
    d.edge("producto", "promo", "assoc", "1", "0..1", "en promocion")
    d.edge("producto", "detalle", "assoc", "1", "0..*", "copiado en")
    d.edge("pedido", "reserva", "assoc", "1", "1..*", "reserva stock")
    d.edge("reserva", "producto", "assoc", "0..*", "1", "de")
    d.edge("pedido", "pago", "assoc", "1", "0..*", "se paga con")
    d.edge("pago", "evweb", "comp", "1", "0..*", "recibe")
    d.edge("pedido", "hecho", "assoc", "1", "0..*", "origina")
    for s, e in (("s_auth", "usuario"), ("s_cat", "producto"), ("s_cli", "cliente"), ("s_ord", "pedido"), ("s_pay", "pago"), ("s_ana", "hecho")):
        d.edge(s, e, "dep")
    return d


def gateway():
    d = Diagram("uml_gateway", "UML API Gateway, politicas y GraphQL Gateway", rankdir="TB")
    d.node("gw", "ApiGateway", "service", "gateway", attrs=["cookie: session_token  «HttpOnly, SameSite=Lax»", "maxBody: 64 KiB", "timeout: 3 s"], ops=["+handle(request): Response", "+login() / logout() / register() / me()"])
    d.node("route", "RouteDefinition", "policy", attrs=["metodo: Verbo", "patron: String", "destino: ServiceTarget", "rutaInterna: String", "acceso: public|optional|session", "limite: String"], ops=["+coincide(metodo, ruta): Params"])
    d.node("authn", "AuthenticationPolicy", "policy", attrs=["cookie: session_token", "expiracion: 900 s"], ops=["+autenticar(request): Identity", "+descartarCabecerasDeIdentidad()"])
    d.node("authz", "AuthorizationPolicy", "policy", attrs=["roles: Set<Rol>"], ops=["+permite(identity, ruta): Boolean"])
    d.node("limit", "RateLimiter", "policy", attrs=["bucket: login|register|webhook|graphql|default", "ventana: 60 s"], ops=["+permitir(bucket, ip): Boolean"])
    d.node("target", "ServiceTarget", "adapter", attrs=["nombre: String", "baseUrl: String"], ops=["+request(metodo, ruta, usuario): Response"])
    d.node("secret", "SecretProvider", "secret", attrs=["ttl: 30 s", "cache: Map"], ops=["+get(ruta): Map", "«fail-closed»"])
    d.node("vault", "VaultClient", "secret", "externo", attrs=["addr: String", "token: archivo montado ro"], ops=["+read(ruta) / write(ruta)"])
    d.node("auth", "AuthService", "service", "servicio privado", ops=["+login / register / introspect / logout"])
    d.node("guard", "ServiceGuard", "policy", "en cada servicio privado", attrs=["permitidos: Set<Llamador>"], ops=["+verificar(llamador, token): Caller", "acepta token vigente o anterior"])
    d.node("gql", "GraphQLGateway", "service", "gateway privado", attrs=["maxDepth: 6", "maxCost: 5000", "maxPage: 50", "introspeccion: off"], ops=["+execute(query, contexto): Result"])
    d.node("schema", "Schema", "policy", attrs=["Query: me, products, product, myOrders, order, salesSummary", "Mutation: createOrder, syncAnalytics"])
    d.node("resolver", "Resolver", "adapter", attrs=["permisos: IsStaff|IsAdmin|CanPay|OwnerOrAdmin"], ops=["+resolver(campo, fuente, contexto)"])
    d.node("loader", "DataLoader", "adapter", attrs=["productos", "clientes", "pagos"], ops=["+load(clave) / lote por solicitud"])
    d.node("limits", "CostLimit / DepthLimit", "policy", "regla de validacion", ops=["+validar(documento): Error?"])
    d.node("grpc", "AnalyticsClient", "adapter", "cliente gRPC", attrs=["canal: insecure (red privada)", "plazo: 5 s / 30 s"], ops=["+summary() / sync() / streamSales()"])
    d.node("ana", "AnalyticsServer", "service", "servicio gRPC", attrs=["interceptor: AuthInterceptor"], ops=["+SalesSummary (unary)", "+StreamSales (server streaming)", "+Sync (unary)"])
    d.node("priv", "InventoryService, ClientService, OrderService, PaymentService", "service", "servicios privados", ops=["REST con X-Service-Caller / X-Service-Token + identidad verificada"])

    d.edge("gw", "route", "comp", "1", "1..*", "define")
    d.edge("route", "target", "assoc", "0..*", "1", "enruta a")
    d.edge("route", "authz", "assoc", "0..*", "1", "exige")
    d.edge("gw", "authn", "comp", "1", "1", "aplica")
    d.edge("gw", "limit", "comp", "1", "1", "aplica")
    d.edge("target", "secret", "dep", label="credencial de arista")
    d.edge("secret", "vault", "assoc", "1", "1", "lee de")
    d.edge("authn", "auth", "dep", label="introspect")
    d.edge("target", "priv", "flow", label="REST privado")
    d.edge("priv", "guard", "comp", "1", "1", "protegido por")
    d.edge("gw", "gql", "flow", label="POST /graphql")
    d.edge("gql", "schema", "comp", "1", "1", "expone")
    d.edge("schema", "resolver", "assoc", "1", "1..*", "resuelve con")
    d.edge("gql", "limits", "comp", "1", "1..*", "valida con")
    d.edge("resolver", "loader", "dep")
    d.edge("loader", "priv", "flow", label="lotes")
    d.edge("resolver", "grpc", "dep")
    d.edge("grpc", "ana", "grpc", label="gRPC")
    return d


def componentes():
    d = Diagram(
        "mapa_componentes",
        "Mapa de componentes y despliegue",
        rankdir="LR",
        clusters={"pub": "Internet", "dmz": "Red publica (compose: public)", "priv": "Red privada (compose: private, internal: true)"},
    )
    d.node("nav", "Navegador\n(frontend responsivo)", "external", lines=["cookie HttpOnly"], cluster="pub")
    d.node("prov", "Proveedor de pagos\n(adaptador de prueba)", "external", lines=["webhook firmado HMAC"], cluster="pub")
    d.node("gw", "API Gateway :8000", "service", lines=["rutas explicitas, roles", "limite de tasa, 64 KiB", "descarta cabeceras de identidad"], cluster="dmz")
    d.node("auth", "Auth Service :8100", "service", lines=["sesiones opacas (hash)", "scrypt + sal"], cluster="priv")
    d.node("gql", "GraphQL Gateway :9200", "adapter", lines=["agregacion, batching", "profundidad/costo/paginas"], cluster="priv")
    d.node("inv", "inventory :9101", "service", lines=["catalogo, stock, reservas"], cluster="priv")
    d.node("cli", "clients :9102", "service", lines=["perfil, datos personales"], cluster="priv")
    d.node("ord", "orders :9103", "service", lines=["pedidos, estados, expiracion"], cluster="priv")
    d.node("pay", "payments :9104", "service", lines=["pagos, webhook, idempotencia"], cluster="priv")
    d.node("ana", "analytics :50051 (gRPC)", "adapter", lines=["lectura de ventas, streaming"], cluster="priv")
    d.node("vault", "Vault :8200", "secret", lines=["KV v2 + politicas por servicio"], cluster="priv")
    for key, name in (("db_auth", "auth.db"), ("db_inv", "inventory.db"), ("db_cli", "clients.db"), ("db_ord", "orders.db"), ("db_pay", "payments.db"), ("db_ana", "analytics.db")):
        d.node(key, name, "store", shape="cylinder", cluster="priv")
    d.edge("nav", "gw", "flow", label="HTTPS (TLS en el borde)")
    d.edge("prov", "gw", "flow", label="POST /payments/webhook")
    d.edge("gw", "auth", "flow", label="introspect / login")
    d.edge("gw", "inv", "flow", label="REST")
    d.edge("gw", "cli", "flow", label="REST")
    d.edge("gw", "ord", "flow", label="REST")
    d.edge("gw", "pay", "flow", label="REST")
    d.edge("gw", "gql", "flow", label="POST /graphql")
    d.edge("gql", "ord", "flow", label="REST")
    d.edge("gql", "inv", "flow", label="REST (lotes)")
    d.edge("gql", "cli", "flow", label="REST (lotes)")
    d.edge("gql", "pay", "flow", label="REST (lotes)")
    d.edge("gql", "ana", "grpc", label="gRPC")
    d.edge("ord", "inv", "flow", label="reservar/liberar/confirmar")
    d.edge("ord", "cli", "flow", label="verificar cliente")
    d.edge("pay", "ord", "flow", label="consultar / pagado")
    d.edge("ana", "ord", "flow", label="export de pagados")
    d.edge("auth", "cli", "flow", label="crear perfil")
    for s, db in (("auth", "db_auth"), ("inv", "db_inv"), ("cli", "db_cli"), ("ord", "db_ord"), ("pay", "db_pay"), ("ana", "db_ana")):
        d.edge(s, db, "assoc")
    for s in ("gw", "gql", "inv", "cli", "ord", "pay", "ana", "auth"):
        d.edge(s, "vault", "secret", constraint=False)
    return d


def main():
    for build in (dominio, gateway, componentes):
        build().render()
        print("ok", build.__name__)


if __name__ == "__main__":
    main()
