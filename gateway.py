import os
import secrets
import httpx
from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    Request,
    Response
)
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials
)

app = FastAPI(
    title="El Mariachi - API Gateway",
    description="API Gateway con Vault y Bearer Token"
)

security = HTTPBearer(auto_error=False)

VAULT_ADDR = os.getenv(
    "VAULT_ADDR",
    "http://127.0.0.1:8200"
)
VAULT_TOKEN = os.getenv("VAULT_TOKEN")

# Los dos backends de El Mariachi (Menú y Pedidos)
BACKEND_MENU = os.getenv(
    "BACKEND_MENU_URL",
    "http://localhost:9000"
)
BACKEND_PEDIDOS = os.getenv(
    "BACKEND_PEDIDOS_URL",
    "http://localhost:9100"
)

if not VAULT_TOKEN:
    raise RuntimeError("VAULT_TOKEN no configurado")

# Qué recurso (primer segmento de la ruta) pertenece a qué backend
RUTAS_MENU = {"platillos", "categorias"}
RUTAS_PEDIDOS = {"pedidos", "reservas"}

# Scope mínimo requerido para leer (GET) y para escribir (POST/PUT/PATCH/DELETE)
SCOPES_LECTURA = {
    "platillos": "menu:read",
    "categorias": "menu:read",
    "pedidos": "pedidos:read",
    "reservas": "pedidos:read"
}
SCOPES_ESCRITURA = {
    "platillos": "menu:write",
    "categorias": "menu:write",
    "pedidos": "pedidos:write",
    "reservas": "pedidos:write"
}


async def get_gateway_secrets():
    url = f"{VAULT_ADDR}/v1/secret/data/gateway"
    headers = {
        "X-Vault-Token": VAULT_TOKEN
    }
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get(url, headers=headers)
        except httpx.RequestError:
            raise HTTPException(
                status_code=500,
                detail="No fue posible acceder al gestor de secretos (Vault)"
            )

    if response.status_code != 200:
        raise HTTPException(
            status_code=500,
            detail="No fue posible acceder a Vault"
        )

    vault_response = response.json()
    return vault_response["data"]["data"]


async def authenticate_client(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Bearer token requerido"
        )

    vault_secrets = await get_gateway_secrets()
    expected_token = vault_secrets["client_token"]
    received_token = credentials.credentials

    valid = secrets.compare_digest(
        received_token,
        expected_token
    )
    if not valid:
        raise HTTPException(
            status_code=401,
            detail="Token invalido"
        )

    return {
        "client_id": vault_secrets.get("client_id", "student-client"),
        "backend_secret": vault_secrets["backend_shared_secret"],
        # Lista de scopes que tiene autorizado este cliente, ej: ["menu:read", "pedidos:read"]
        "scopes": vault_secrets.get("client_scopes", [])
    }


def resolver_backend(primer_segmento: str) -> str:
    if primer_segmento in RUTAS_MENU:
        return BACKEND_MENU
    if primer_segmento in RUTAS_PEDIDOS:
        return BACKEND_PEDIDOS
    raise HTTPException(
        status_code=404,
        detail=f"Ruta '{primer_segmento}' no reconocida por el Gateway"
    )


def verificar_scope(primer_segmento: str, metodo: str, scopes_cliente: list):
    mapa_scopes = SCOPES_LECTURA if metodo == "GET" else SCOPES_ESCRITURA
    scope_requerido = mapa_scopes.get(primer_segmento)

    if scope_requerido and scope_requerido not in scopes_cliente:
        raise HTTPException(
            status_code=403,
            detail=f"El cliente no tiene el scope requerido: {scope_requerido}"
        )


@app.get("/health")
def health():
    return {
        "status": "OK",
        "service": "El Mariachi - API Gateway"
    }


@app.api_route(
    "/api/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"]
)
async def proxy(
    path: str,
    request: Request,
    auth=Depends(authenticate_client)
):
    primer_segmento = path.split("/")[0]

    # Autorización por roles/scopes (403 si no tiene permiso)
    verificar_scope(primer_segmento, request.method, auth["scopes"])

    # Decide a qué backend enrutar según el recurso solicitado
    backend_destino = resolver_backend(primer_segmento)
    target_url = f"{backend_destino}/{path}"

    body = await request.body()

    # El Gateway usa SU PROPIO secreto interno hacia el backend,
    # nunca reenvía el token original del cliente
    gateway_headers = {
        "X-Gateway-Secret": auth["backend_secret"],
        "X-Authenticated-Client": auth["client_id"]
    }
    content_type = request.headers.get("content-type")
    if content_type:
        gateway_headers["content-type"] = content_type

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            upstream = await client.request(
                method=request.method,
                url=target_url,
                params=request.query_params,
                content=body,
                headers=gateway_headers
            )
    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="Backend no disponible"
        )

    response_headers = {}
    if "content-type" in upstream.headers:
        response_headers["content-type"] = upstream.headers["content-type"]

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers
    )