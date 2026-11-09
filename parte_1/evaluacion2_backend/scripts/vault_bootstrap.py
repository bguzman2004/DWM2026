import argparse
import os
import secrets as pysecrets
import stat
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.topology import APP_SECRETS, EDGES, SERVICES, callees_of, edge_path
from common.vault import VaultClient


def new_secret():
    return pysecrets.token_urlsafe(32)


def policy_for(service):
    paths = [f"secret/data/mariachi/edges/{service}/*"]
    paths += [f"secret/data/{edge_path(callee, service)}" for callee in callees_of(service)]
    paths += [f"secret/data/{p}" for p in APP_SECRETS.get(service, ())]
    return "\n".join(f'path "{p}" {{ capabilities = ["read"] }}' for p in paths) + "\n"


def bootstrap(vault):
    for caller, callee in EDGES:
        path = edge_path(callee, caller)
        if not vault.exists(path):
            vault.write(path, {"token": new_secret()})
    for service, paths in APP_SECRETS.items():
        for path in paths:
            if not vault.exists(path):
                vault.write(path, {"webhook_hmac": new_secret()})
    tokens = {}
    for service in SERVICES:
        name = f"mariachi-{service}"
        vault.put_policy(name, policy_for(service))
        tokens[service] = vault.create_token([name])
    return tokens


def rotate_edge(vault, caller, callee):
    path = edge_path(callee, caller)
    current = vault.read(path)
    vault.write(path, {"token": new_secret(), "previous": current["token"]})


def revoke_previous_edge(vault, caller, callee):
    path = edge_path(callee, caller)
    current = vault.read(path)
    vault.write(path, {"token": current["token"]})


def rotate_webhook(vault):
    current = vault.read("mariachi/payments")
    vault.write("mariachi/payments", {"webhook_hmac": new_secret(), "previous": current["webhook_hmac"]})


def revoke_previous_webhook(vault):
    current = vault.read("mariachi/payments")
    vault.write("mariachi/payments", {"webhook_hmac": current["webhook_hmac"]})


def write_token_files(tokens, directory):
    for service, token in tokens.items():
        folder = os.path.join(directory, service)
        os.makedirs(folder, exist_ok=True)
        target = os.path.join(folder, "token")
        with open(target, "w") as handle:
            handle.write(token)
        os.chmod(target, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--token-dir", required=True)
    parser.add_argument("--rotate-edge", nargs=2, metavar=("CALLER", "CALLEE"))
    parser.add_argument("--revoke-previous-edge", nargs=2, metavar=("CALLER", "CALLEE"))
    parser.add_argument("--rotate-webhook", action="store_true")
    parser.add_argument("--revoke-previous-webhook", action="store_true")
    args = parser.parse_args()
    vault = VaultClient(os.environ["VAULT_ADDR"], os.environ["VAULT_ROOT_TOKEN"])
    if args.rotate_edge:
        rotate_edge(vault, *args.rotate_edge)
        print("rotado")
    elif args.revoke_previous_edge:
        revoke_previous_edge(vault, *args.revoke_previous_edge)
        print("anterior revocado")
    elif args.rotate_webhook:
        rotate_webhook(vault)
        print("rotado")
    elif args.revoke_previous_webhook:
        revoke_previous_webhook(vault)
        print("anterior revocado")
    else:
        write_token_files(bootstrap(vault), args.token_dir)
        print("secretos y politicas listos")


if __name__ == "__main__":
    main()
