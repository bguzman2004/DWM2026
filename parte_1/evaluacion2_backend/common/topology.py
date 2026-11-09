SERVICES = (
    "api-gateway",
    "auth",
    "inventory",
    "clients",
    "orders",
    "payments",
    "graphql-gateway",
    "analytics",
)

EDGES = (
    ("api-gateway", "auth"),
    ("api-gateway", "inventory"),
    ("api-gateway", "clients"),
    ("api-gateway", "orders"),
    ("api-gateway", "payments"),
    ("api-gateway", "graphql-gateway"),
    ("graphql-gateway", "orders"),
    ("graphql-gateway", "inventory"),
    ("graphql-gateway", "clients"),
    ("graphql-gateway", "payments"),
    ("graphql-gateway", "analytics"),
    ("orders", "inventory"),
    ("orders", "clients"),
    ("payments", "orders"),
    ("analytics", "orders"),
    ("auth", "clients"),
)

APP_SECRETS = {
    "payments": ("mariachi/payments",),
}

ROLES = ("customer", "kitchen", "admin")


def edge_path(callee, caller):
    return f"mariachi/edges/{callee}/{caller}"


def callees_of(service):
    return [callee for caller, callee in EDGES if caller == service]


def callers_of(service):
    return [caller for caller, callee in EDGES if callee == service]


def probe_path(service):
    outgoing = callees_of(service)
    if outgoing:
        return edge_path(outgoing[0], service)
    return edge_path(service, callers_of(service)[0])
