import os
import secrets

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="El Mariachi - Backend API",
    description="Lógica de negocio. Solo acepta solicitudes provenientes del Gateway"
)

INTERNAL_GATEWAY_SECRET = os.getenv("INTERNAL_GATEWAY_SECRET")
if not INTERNAL_GATEWAY_SECRET:
    raise RuntimeError("INTERNAL_GATEWAY_SECRET no esta configurado")

PLATILLOS_INICIALES = [
    {"id": 1, "nombre": "Tacos al Pastor", "categoria": "Tacos", "precio": 2500},
    {"id": 2, "nombre": "Burrito Especial", "categoria": "Burritos", "precio": 4500},
    {"id": 3, "nombre": "Nachos Supreme", "categoria": "Nachos", "precio": 3500}
]

CATEGORIAS = [
    {"id": 1, "nombre": "Tacos"},
    {"id": 2, "nombre": "Burritos"},
    {"id": 3, "nombre": "Nachos"}
]

PEDIDOS = [
    {"id": 1001, "cliente": "Camila Rojas", "total": 7000, "estado": "pagado"},
    {"id": 1002, "cliente": "Matías Cañete", "total": 3500, "estado": "pendiente"}
]

PLATILLOS = [dict(p) for p in PLATILLOS_INICIALES]


class PlatilloIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    categoria: str = Field(min_length=1, max_length=40)
    precio: int = Field(gt=0)


def verify_gateway(
    x_gateway_secret: str = Header(default="")
):
    valid = secrets.compare_digest(
        x_gateway_secret.encode(),
        INTERNAL_GATEWAY_SECRET.encode()
    )
    if not valid:
        raise HTTPException(
            status_code=403,
            detail="Solicitud no autorizada desde Gateway"
        )


def get_identity(
    x_authenticated_user: str | None = Header(default=None),
    x_authenticated_username: str | None = Header(default=None),
    x_authenticated_roles: str | None = Header(default=None)
):
    roles = [r for r in (x_authenticated_roles or "").split(",") if r]
    return {
        "user_id": x_authenticated_user,
        "username": x_authenticated_username,
        "roles": roles
    }


def require_admin(identity: dict = Depends(get_identity)):
    if "admin" not in identity["roles"]:
        raise HTTPException(
            status_code=403,
            detail="Se requiere rol admin"
        )
    return identity


@app.get("/health")
def health():
    return {
        "status": "OK",
        "service": "El Mariachi - Backend API"
    }


@app.get("/platillos", dependencies=[Depends(verify_gateway)])
def listar_platillos(identity: dict = Depends(get_identity)):
    return {"identity": identity, "platillos": PLATILLOS}


@app.get("/categorias", dependencies=[Depends(verify_gateway)])
def listar_categorias(identity: dict = Depends(get_identity)):
    return {"identity": identity, "categorias": CATEGORIAS}


@app.get("/pedidos", dependencies=[Depends(verify_gateway)])
def listar_pedidos(identity: dict = Depends(get_identity)):
    return {"identity": identity, "pedidos": PEDIDOS}


@app.post(
    "/platillos",
    status_code=201,
    dependencies=[Depends(verify_gateway)]
)
def crear_platillo(
    platillo: PlatilloIn,
    identity: dict = Depends(require_admin)
):
    nuevo_id = max((p["id"] for p in PLATILLOS), default=0) + 1
    nuevo = {"id": nuevo_id, **platillo.model_dump()}
    PLATILLOS.append(nuevo)
    return {"identity": identity, "platillo": nuevo}


@app.delete("/platillos/{platillo_id}", dependencies=[Depends(verify_gateway)])
def eliminar_platillo(
    platillo_id: int,
    identity: dict = Depends(require_admin)
):
    for index, platillo in enumerate(PLATILLOS):
        if platillo["id"] == platillo_id:
            PLATILLOS.pop(index)
            return {"identity": identity, "deleted": platillo_id}
    raise HTTPException(
        status_code=404,
        detail="Platillo no encontrado"
    )
