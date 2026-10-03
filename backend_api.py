import os
import secrets

from fastapi import (
    FastAPI,
    Header,
    HTTPException,
    Depends
)

app = FastAPI(
    title="El Mariachi - API Menú (Protegida)",
    description="API de platillos, ubicada y enrutada por API Gateway"
)

INTERNAL_GATEWAY_SECRET = os.getenv(
    "INTERNAL_GATEWAY_SECRET"
)
if not INTERNAL_GATEWAY_SECRET:
    raise RuntimeError(
        "INTERNAL_GATEWAY_SECRET no esta configurado"
    )


def verify_gateway(
    x_gateway_secret: str = Header(default="")
):
    valid = secrets.compare_digest(
        x_gateway_secret,
        INTERNAL_GATEWAY_SECRET
    )
    if not valid:
        raise HTTPException(
            status_code=403,
            detail="Solicitud no autorizada desde Gateway"
        )


@app.get(
    "/health",
    dependencies=[Depends(verify_gateway)]
)
def health(
    x_authenticated_client: str | None = Header(default=None)
):
    return {
        "authenticated_client": x_authenticated_client,
        "status": "OK",
        "service": "El Mariachi - API Menú"
    }


@app.get(
    "/platillos",
    dependencies=[Depends(verify_gateway)]
)
def platillos(
    x_authenticated_client: str | None = Header(default=None),
    x_authenticated_user: str | None = Header(default=None),
    x_authenticated_roles: str | None = Header(default=None)
):
    return {
        "identity": {
            "client_id": x_authenticated_client,
            "username": x_authenticated_user,
            "roles": x_authenticated_roles
        },
        "platillos": [
            {"id": 1, "nombre": "Tacos al Pastor", "categoria": "Tacos", "precio": 2500},
            {"id": 2, "nombre": "Burrito Especial", "categoria": "Burritos", "precio": 4500},
            {"id": 3, "nombre": "Nachos Supreme", "categoria": "Nachos", "precio": 3500}
        ]
    }


@app.get(
    "/categorias",
    dependencies=[Depends(verify_gateway)]
)
def categorias(
    x_authenticated_client: str | None = Header(default=None),
    x_authenticated_user: str | None = Header(default=None),
    x_authenticated_roles: str | None = Header(default=None)
):
    return {
        "identity": {
            "client_id": x_authenticated_client,
            "username": x_authenticated_user,
            "roles": x_authenticated_roles
        },
        "categorias": [
            {"id": 1, "nombre": "Tacos"},
            {"id": 2, "nombre": "Burritos"},
            {"id": 3, "nombre": "Nachos"}
        ]
    }