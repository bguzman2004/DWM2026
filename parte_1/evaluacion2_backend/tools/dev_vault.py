import re

from fastapi import FastAPI, Header, HTTPException, Request


def create_dev_vault(root_token):
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    store = {}
    policies = {}
    tokens = {}
    state = {"down": False, "reads": []}
    app.state.store = store
    app.state.policies = policies
    app.state.tokens = tokens
    app.state.state = state

    def allowed(token, path, capability):
        if token == root_token:
            return True
        rules = tokens.get(token)
        if rules is None:
            return False
        for pattern, caps in rules:
            if capability not in caps:
                continue
            if pattern.endswith("*"):
                if path.startswith(pattern[:-1]):
                    return True
            elif path == pattern:
                return True
        return False

    def parse_policy(hcl):
        rules = []
        for match in re.finditer(r'path\s+"([^"]+)"\s*\{\s*capabilities\s*=\s*\[([^\]]*)\]', hcl):
            caps = re.findall(r'"([^"]+)"', match.group(2))
            rules.append((match.group(1), caps))
        return rules

    def check(token, path, capability):
        if state["down"]:
            raise HTTPException(503, "sealed")
        if token is None or (token != root_token and token not in tokens):
            raise HTTPException(403, "permission denied")
        if not allowed(token, path, capability):
            raise HTTPException(403, "permission denied")

    @app.get("/v1/secret/data/{path:path}")
    def read(path: str, x_vault_token: str | None = Header(None)):
        check(x_vault_token, f"secret/data/{path}", "read")
        state["reads"].append((x_vault_token, path))
        if path not in store:
            raise HTTPException(404, "not found")
        return {"data": {"data": store[path], "metadata": {"version": 1}}}

    @app.post("/v1/secret/data/{path:path}")
    async def write(path: str, request: Request, x_vault_token: str | None = Header(None)):
        check(x_vault_token, f"secret/data/{path}", "update")
        body = await request.json()
        store[path] = body["data"]
        return {"data": {"version": 1}}

    @app.put("/v1/sys/policies/acl/{name}")
    async def put_policy(name: str, request: Request, x_vault_token: str | None = Header(None)):
        check(x_vault_token, f"sys/policies/acl/{name}", "update")
        body = await request.json()
        policies[name] = parse_policy(body["policy"])
        return {}

    @app.post("/v1/auth/token/create")
    async def create_token(request: Request, x_vault_token: str | None = Header(None)):
        check(x_vault_token, "auth/token/create", "update")
        body = await request.json()
        import secrets as pysecrets

        token = "hvs." + pysecrets.token_urlsafe(24)
        rules = []
        for name in body.get("policies", []):
            rules.extend(policies.get(name, []))
        tokens[token] = rules
        return {"auth": {"client_token": token, "policies": body.get("policies", [])}}

    return app
