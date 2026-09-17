from fastapi import FastAPI

app = FastAPI(
    title="El Mariachi - API Pedidos",
    description="API de pedidos y reservas, ubicada y enrutada por API Gateway"
)

@app.get("/salud")
def salud():
    return {
        "status": "OK",
        "service": "El Mariachi - API Pedidos"
    }

@app.get("/pedidos")
def pedidos():
    return {
        "pedidos": [
            {"id": 1001, "cliente": "Benjamín", "status": "pagado"},
            {"id": 1002, "cliente": "Matías", "status": "pendiente"}
        ]
    }

@app.get("/reservas")
def reservas():
    return {
        "reservas": [
            {"id": 501, "cliente": "María", "personas": 4, "hora": "20:00"},
            {"id": 502, "cliente": "Omar", "personas": 2, "hora": "21:30"}
        ]
    }