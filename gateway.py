import os
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
from pydantic import BaseModel

app = FastAPI(title="El Mariachi - API Gateway")

security = HTTPBearer(auto_error=False)

AUTH_SERVICE_URL = os.getenv(
    "AUTH_SERVICE_URL",
    "http://127.0.0.1:8100"
)

VAULT_ADDR = os.getenv(
    "VAULT_ADDR", "http://127.0.0.1:8200"
)

VAULT_TOKEN = os.getenv(
    "VAULT_TOKEN"
)

BACKEND_MENU = os.getenv(
    "BACKEND_MENU_URL",
    "http://localhost:9000"
)
BACKEND_PEDIDOS = os.getenv(
    "BACKEND_PEDIDOS_URL",
    "http://localhost:9100"
)

if not VAULT_TOKEN:
    raise RuntimeError(
        "VAULT_TOKEN no está configurado"
    )

RUTAS_MENU = {"platillos", "categorias"}
RUTAS_PEDIDOS = {"pedidos", "reservas"}


async def get_gateway_secrets():
    url = (
        f"{VAULT_ADDR}"
        "/v1/secret/data/gateway"
    )
    headers = {
        "X-Vault-Token": VAULT_TOKEN
    }

    async with httpx.AsyncClient(
        timeout=5.0
    ) as client:
        response = await client.get(
            url,
            headers=headers
        )
    if response.status_code != 200:
        raise HTTPException(
            status_code=500,
            detail="No fue posible acceder a Vault"
        )
    vault_response = response.json()
    return vault_response[
        "data"
    ][
        "data"
    ]


async def authenticate_client(
        credentials:
            HTTPAuthorizationCredentials
            = Depends(security)
):
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Bearer token requerido"
        )
    gateway_secrets = (
        await get_gateway_secrets()
    )
    introspection_secret = (
        gateway_secrets["auth_introspection_secret"]
    )
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{AUTH_SERVICE_URL}/introspect",
                json={"token": credentials.credentials},
                headers={
                    "X-Gateway-Auth-Secret": introspection_secret
                }
            )
    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="Error consultando Authentication Service"
        )
    if response.status_code == 403:
        raise HTTPException(
            status_code=500,
            detail="Gateway no autorizado ante el Authentication Service (revisa el secreto en Vault)"
        )
    identity = response.json()
    if not identity.get("active", False):
        raise HTTPException(
            status_code=401,
            detail="Token invalido o expirado"
        )
    return {
        "user_id": identity["user_id"],
        "username": identity["username"],
        "roles": identity["roles"],
        "backend_secret": gateway_secrets["backend_shared_secret"],
        "introspection_secret": introspection_secret
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


def verificar_rol(metodo: str, roles: list):
    if metodo in ("POST", "PUT", "PATCH", "DELETE") and "admin" not in roles:
        raise HTTPException(
            status_code=403,
            detail="El usuario no tiene permisos para esta operación"
        )


@app.get("/health")
def health():
    return {
        "status": "OK",
        "service": "El Mariachi - API Gateway"
    }


class LoginRequest(BaseModel):
    username: str
    password: str


def respuesta_del_auth(response: httpx.Response) -> Response:
    headers = {}
    if "retry-after" in response.headers:
        headers["retry-after"] = response.headers["retry-after"]
    return Response(
        content=response.content,
        status_code=response.status_code,
        media_type="application/json",
        headers=headers
    )


@app.post("/auth/login")
async def login(datos: LoginRequest):
    gateway_secrets = await get_gateway_secrets()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{AUTH_SERVICE_URL}/login",
                json=datos.model_dump(),
                headers={
                    "X-Gateway-Auth-Secret": gateway_secrets["auth_introspection_secret"]
                }
            )
    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="Error consultando Authentication Service"
        )
    return respuesta_del_auth(response)


@app.post("/auth/logout")
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth=Depends(authenticate_client)
):
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{AUTH_SERVICE_URL}/logout",
                json={"token": credentials.credentials},
                headers={
                    "X-Gateway-Auth-Secret": auth["introspection_secret"]
                }
            )
    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="Error consultando Authentication Service"
        )
    return respuesta_del_auth(response)


@app.api_route(
    "/api/{path:path}",
    methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE"
    ]
)
async def proxy(
    path: str,
    request: Request,
    auth=Depends(authenticate_client)
):
    segmentos = path.split("/")
    if any(seg in (".", "..") for seg in segmentos):
        raise HTTPException(
            status_code=400,
            detail="Ruta no válida"
        )
    primer_segmento = segmentos[0]

    verificar_rol(request.method, auth["roles"])

    backend_destino = resolver_backend(primer_segmento)
    target_url = f"{backend_destino}/{path}"

    body = await request.body()

    gateway_headers = {
        "X-Gateway-Secret":
            auth["backend_secret"],
        "X-Authenticated-Client":
            auth["user_id"],
        "X-Authenticated-User":
            auth["username"],
        "X-Authenticated-Roles":
            ",".join(auth["roles"])
    }
    content_type = request.headers.get(
        "content-type"
    )
    if content_type:
        gateway_headers[
            "content-type"
        ] = content_type
    try:
        async with httpx.AsyncClient(
            timeout=10.0
        ) as client:
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
        response_headers[
            "content-type"
        ] = upstream.headers[
            "content-type"
        ]

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers
    )