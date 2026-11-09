import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

MUTANTES = [
    (
        "M1 orders deja de comprobar la propiedad del pedido",
        "services/orders/main.py",
        'if user.has("customer") and user.client_id == order["client_id"]:\n            return order',
        'if user.has("customer"):\n            return order',
        "tests/test_security.py::test_propiedad_de_ordenes_entre_clientes",
    ),
    (
        "M2 payments deja de deduplicar avisos por event_id",
        "services/payments/main.py",
        '"SELECT 1 FROM webhook_events WHERE event_id = ?"',
        '"SELECT 1 FROM webhook_events WHERE event_id = ? AND 0"',
        "tests/test_payments.py::test_webhook_duplicado_no_paga_dos_veces",
    ),
    (
        "M3 inventory reserva sin comprobar disponibilidad",
        "services/inventory/main.py",
        "WHERE product_id = ? AND on_hand - reserved >= ?\",\n                    (qty, product_id, qty),",
        "WHERE product_id = ?\",\n                    (qty, product_id),",
        "tests/test_orders_stock.py::test_no_se_puede_vender_mas_de_lo_que_hay",
    ),
    (
        "M4 el gateway abre POST /products a cualquier rol",
        "services/api_gateway/routes.py",
        'Route("POST", "/products", "inventory", "/products", "session", ADMIN)',
        'Route("POST", "/products", "inventory", "/products", "session", ANY)',
        "tests/test_security.py::test_gateway_corta_antes_de_llamar_al_servicio",
    ),
    (
        "M5 los servicios aceptan llamadores fuera de la topología",
        "common/security.py",
        "if caller not in allowed or not token:",
        "if not token:",
        "tests/test_security.py::test_llamador_fuera_de_la_topologia_es_rechazado",
    ),
    (
        "M6 orders acepta un monto de pago distinto del total",
        "services/orders/main.py",
        'if body.amount != row["total"]:',
        "if False:",
        "tests/test_payments.py::test_orders_valida_el_monto_aunque_el_aviso_venga_de_payments",
    ),
    (
        "M7 payments acepta cualquier firma del webhook",
        "services/payments/main.py",
        "if not x_signature or not valid_signature(raw, x_signature):",
        "if False:",
        "tests/test_payments.py::test_firma_invalida_o_ausente",
    ),
    (
        "M8 GraphQL sin límite de costo",
        "services/graphql_gateway/limits.py",
        "if total > max_cost:",
        "if False:",
        "tests/test_graphql.py::test_limite_de_costo_rechaza_consultas_abusivas",
    ),
    (
        "M9 la promoción 2x1 deja de aplicarse en el servidor",
        "services/inventory/main.py",
        "return (qty // 2) * unit_price",
        "return 0",
        "tests/test_frontend_flujos.py::test_p01_promocion_del_dia_se_aplica_en_el_servidor",
    ),
    (
        "M10 el servidor deja de validar el teléfono",
        "common/validators.py",
        "    if not found:\n        raise ValueError",
        "    if False:\n        raise ValueError",
        "tests/test_frontend_flujos.py::test_p03_formulario_del_frontend_valida_contacto_en_el_servidor",
    ),
]


def correr(carpeta, prueba):
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-x", "--no-header", "-p", "no:cacheprovider", "--show-capture=no", prueba],
        cwd=carpeta,
        capture_output=True,
        text=True,
        timeout=300,
    )
    return r.returncode, r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-200:]


def main():
    resultados = []
    with tempfile.TemporaryDirectory() as tmp:
        copia = Path(tmp) / "repo"
        shutil.copytree(ROOT, copia, ignore=shutil.ignore_patterns("__pycache__", "*.db", ".pytest_cache", "bench", "docs"))
        for nombre, archivo, original, mutado, prueba in MUTANTES:
            ruta = copia / archivo
            texto = ruta.read_text()
            assert texto.count(original) == 1, f"{nombre}: fragmento no encontrado"
            codigo_base, _ = correr(copia, prueba)
            ruta.write_text(texto.replace(original, mutado))
            try:
                codigo, resumen = correr(copia, prueba)
            finally:
                ruta.write_text(texto)
            fila = {
                "mutante": nombre,
                "archivo": archivo,
                "prueba": prueba.split("::")[1],
                "sin_mutar": "pasa" if codigo_base == 0 else "FALLA",
                "con_mutacion": "falla (detectado)" if codigo != 0 else "pasa (NO detectado)",
                "detalle": resumen,
            }
            resultados.append(fila)
            print(f"{nombre}: {fila['sin_mutar']} -> {fila['con_mutacion']}")
    (ROOT / "docs/evidencia/mutaciones.json").write_text(json.dumps(resultados, indent=2, ensure_ascii=False))
    detectados = sum(1 for r in resultados if r["con_mutacion"].startswith("falla") and r["sin_mutar"] == "pasa")
    print(f"{detectados}/{len(resultados)} mutantes detectados")


if __name__ == "__main__":
    main()
