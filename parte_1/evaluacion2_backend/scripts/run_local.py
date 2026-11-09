import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.support.stack import DEMO_PASSWORD, ROOT_TOKEN, Stack


def main():
    port = int(os.getenv("GATEWAY_PORT", "8000"))
    folder = Path(tempfile.mkdtemp(prefix="mariachi-"))
    stack = Stack(folder, extra={"api-gateway": {"limits": {}}})
    stack.ports["api-gateway"] = port
    stack.urls["api-gateway"] = f"http://127.0.0.1:{port}"
    stack.start()
    print("Sistema local levantado (Vault de desarrollo en memoria, un solo proceso)")
    print("Gateway:", stack.urls["api-gateway"])
    privados = ", ".join(f"{n} {u}" for n, u in stack.urls.items() if n not in ("api-gateway", "analytics"))
    print("Servicios privados (deben responder 403 si se llaman directo):", privados)
    print("Vault:", stack.vault_url, "token raiz:", ROOT_TOKEN)
    print("Usuarios: camila, matias (customer), cocina (kitchen), benjamin (admin). Clave:", DEMO_PASSWORD)
    print("Datos en:", folder)
    print("Ctrl+C para detener")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stack.stop()


if __name__ == "__main__":
    main()
