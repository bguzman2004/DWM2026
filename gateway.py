from fastapi import FastAPI
import httpx

app = FastAPI(title="El Mariachi - API Gateway")

BACKEND_MENU = "http://localhost:9000"
BACKEND_PEDIDOS = "http://localhost:9100"

@app.get("/api/platillos")
async def platillos():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BACKEND_MENU}/platillos"
        )
    return response.json()

@app.get("/api/categorias")
async def categorias():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BACKEND_MENU}/categorias"
        )
    return response.json()

@app.get("/api/pedidos")
async def pedidos():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BACKEND_PEDIDOS}/pedidos"
        )
    return response.json()

@app.get("/api/reservas")
async def reservas():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BACKEND_PEDIDOS}/reservas"
        )
    return response.json()