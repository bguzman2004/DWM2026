# El Mariachi — Entrega Evaluación 1 y Evaluación 2

Desarrollo Web y Móvil (DWM2026) · Benjamín Guzmán · Matías Cañete

Caso: El Mariachi, restaurante de comida mexicana. Número en el listado de casos: **por completar**

| Carpeta | Evaluación | Contenido |
|---|---|---|
| [`evaluacion1_frontend/`](evaluacion1_frontend/) | Evaluación 1 · Frontend responsivo | `index.html`, `style.css`, `script.js` e imágenes |
| [`evaluacion2_backend/`](evaluacion2_backend/) | Evaluación 2 · Backend seguro completo | Código, pruebas y su README, que es el informe ([`evaluacion2_backend/README.md`](evaluacion2_backend/README.md)) |

## Evaluación 1 · Frontend

Abrir `evaluacion1_frontend/index.html` en el navegador. Bootstrap, Font Awesome y las fuentes se cargan desde internet. También se puede servir en local:

```bash
cd evaluacion1_frontend
python -m http.server 8080      # abrir http://localhost:8080
```

| Vista | Qué hace |
|---|---|
| Inicio | Portada, Pedido Rápido por WhatsApp y promoción del día (2x1 en Tacos al Pastor) |
| Menú | 12 platillos en 5 categorías, búsqueda (sin importar tildes) y filtros |
| Detalle | Descripción, cantidad y aviso de la promoción |
| Pedido | Carrito con cantidades (+/−, máximo 20 por platillo), subtotal, descuento 2x1 y total; formulario validado (nombre, celular chileno, correo opcional, notas de hasta 200 caracteres) |
| Confirmación | Número de orden, fecha, cliente, teléfono, notas, ítems y totales |
| Nosotros y Contacto | Texto institucional, dirección, horario, mapa y WhatsApp |

El carrito se guarda en el navegador, así que no se pierde al recargar la página.

## Evaluación 2 · Backend

Por indicación del docente, el backend se evalúa con los *datos del frontend*, sin integrar las pantallas. El backend usa el mismo menú del frontend: mismos ids, nombres, categorías y precios, y la misma promoción 2x1. Una prueba automática compara los 12 platillos uno por uno.

```bash
cd evaluacion2_backend
pip install -r requirements-dev.txt
python -m scripts.run_local      # gateway en http://127.0.0.1:8000
python -m pytest tests -q        # 136 pruebas
```

Instrucciones completas, los 10 módulos del informe y las evidencias: [`evaluacion2_backend/README.md`](evaluacion2_backend/README.md).
