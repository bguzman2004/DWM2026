from typing import List, Optional, Dict
from itertools import count

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from contextlib import asynccontextmanager

#Configuration BD mongodb
MONGODB_URI = "mongodb://localhost:27017"
DB_NAME = "dwm2026"
COLL_NAME = "platillos"

client: AsyncIOMotorClient | None = None
db = None
coll = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global client, db, coll
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DB_NAME]
    coll = db[COLL_NAME]
    yield
    client.close()

app = FastAPI(title="El Mariachi API", version="1.0.0", lifespan=lifespan)

class Platillo(BaseModel):
    nombre: str = Field(min_length=1, description="Nombre del platillo")
    categoria: str = Field(min_length=1, description="Categoría: Tacos, Burritos, Nachos, etc.")
    precio: float = Field(gt=0, description="Precio > 0")
    descripcion: Optional[str] = Field(default="", description="Descripción del platillo")

class PlatilloIn(BaseModel):
    nombre: str = Field(min_length=1, description="Nombre del platillo")
    categoria: str = Field(min_length=1, description="Categoría: Tacos, Burritos, Nachos, etc.")
    precio: float = Field(gt=0, description="Precio > 0")
    descripcion: Optional[str] = Field(default="", description="Descripción del platillo")

class PlatilloOut(Platillo):
    id: str

def doc_to_platilloout(doc) -> PlatilloOut:
    return PlatilloOut(
        id = str(doc["_id"]),
        nombre = doc["nombre"],
        categoria = doc["categoria"],
        precio = doc["precio"],
        descripcion = doc.get("descripcion", "")
    )


@app.get("/health", tags=["sistema"])
def health():
    return {"status": "ok"}

@app.get("/platillos", response_model=List[PlatilloOut])
async def listar_platillos(
    q: Optional[str] = Query(None, description="Filtro por nombre que contenga q"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    query = {}
    if q:
        query["nombre"] = {"$regex": q, "$options": "i"}
    cursor = coll.find(query).skip(skip).limit(limit)
    platillos: List[PlatilloOut] = []
    async for doc in cursor:
        platillos.append(doc_to_platilloout(doc))
    return platillos

@app.post("/platillos", response_model=PlatilloOut, status_code=201, tags=["platillos"])
async def crear_platillo(platillo: PlatilloIn):
    res = await coll.insert_one(platillo.model_dump())
    doc = await coll.find_one({"_id": res.inserted_id})
    return doc_to_platilloout(doc)


# http://localhost:8098/platillos/<id>
@app.get("/platillos/{platillo_id}", response_model=PlatilloOut, status_code=201)
async def obtener_platillo(platillo_id: str):
    if not ObjectId.is_valid(platillo_id):
        raise HTTPException(400, "id invalido")
    doc = await coll.find_one({"_id": ObjectId(platillo_id)})
    if not doc:
        raise HTTPException(404, "Platillo no encontrado")
    return doc_to_platilloout(doc)

@app.put("/platillos/{platillo_id}", response_model=PlatilloOut)
async def actualizar_platillo(platillo_id: str, platillo: PlatilloIn):
    if not ObjectId.is_valid(platillo_id):
        raise HTTPException(400, "id invalido")
    res = await coll.update_one(
        {"_id": ObjectId(platillo_id)},
        {"$set": platillo.model_dump()}
    )
    if res.matched_count == 0:
        raise HTTPException(404, "Platillo no encontrado")
    doc = await coll.find_one({"_id": ObjectId(platillo_id)})
    return doc_to_platilloout(doc)

@app.delete("/platillos/{platillo_id}", status_code=204, tags=["platillos"])
async def eliminar_platillo(platillo_id: str):
    if not ObjectId.is_valid(platillo_id):
        raise HTTPException(400, "id invalido")
    res = await coll.delete_one({"_id": ObjectId(platillo_id)})
    if res.deleted_count == 0:
        raise HTTPException(404, "Platillo no encontrado")
    return None