import re
from dataclasses import dataclass

CUSTOMER = ("customer",)
STAFF = ("kitchen", "admin")
ADMIN = ("admin",)
ANY = ()


@dataclass(frozen=True)
class Route:
    method: str
    pattern: str
    upstream: str
    path: str
    access: str
    roles: tuple
    limit: str = "default"

    @property
    def regex(self):
        return re.compile("^" + re.sub(r"\{(\w+)\}", r"(?P<\1>[A-Za-z0-9_-]+)", self.pattern) + "$")


ROUTES = (
    Route("POST", "/payments/webhook", "payments", "/payments/webhook", "public", ANY, "webhook"),
    Route("GET", "/products", "inventory", "/products", "optional", ANY),
    Route("GET", "/products/{id}", "inventory", "/products/{id}", "optional", ANY),
    Route("POST", "/products", "inventory", "/products", "session", ADMIN),
    Route("PATCH", "/products/{id}", "inventory", "/products/{id}", "session", ADMIN),
    Route("DELETE", "/products/{id}", "inventory", "/products/{id}", "session", ADMIN),
    Route("GET", "/promotions", "inventory", "/promotions", "optional", ANY),
    Route("PATCH", "/promotions/{id}", "inventory", "/promotions/{id}", "session", ADMIN),
    Route("GET", "/stock", "inventory", "/stock", "session", STAFF),
    Route("POST", "/stock/{id}/adjust", "inventory", "/stock/{id}/adjust", "session", STAFF),
    Route("GET", "/clients", "clients", "/clients", "session", ADMIN),
    Route("POST", "/clients", "clients", "/clients", "session", ADMIN),
    Route("GET", "/clients/{id}", "clients", "/clients/{id}", "session", ANY),
    Route("PATCH", "/clients/{id}", "clients", "/clients/{id}", "session", CUSTOMER + ADMIN),
    Route("POST", "/orders", "orders", "/orders", "session", CUSTOMER),
    Route("GET", "/orders", "orders", "/orders", "session", ANY),
    Route("POST", "/orders/expire-pending", "orders", "/orders/expire-pending", "session", ADMIN),
    Route("POST", "/orders/reconcile-stock", "orders", "/orders/reconcile-stock", "session", ADMIN),
    Route("GET", "/orders/{id}", "orders", "/orders/{id}", "session", ANY),
    Route("POST", "/orders/{id}/cancel", "orders", "/orders/{id}/cancel", "session", CUSTOMER + ADMIN),
    Route("PATCH", "/orders/{id}/status", "orders", "/orders/{id}/status", "session", STAFF),
    Route("POST", "/payments", "payments", "/payments", "session", CUSTOMER),
    Route("GET", "/payments", "payments", "/payments", "session", CUSTOMER + ADMIN),
    Route("POST", "/payments/reconcile", "payments", "/payments/reconcile", "session", ADMIN),
    Route("GET", "/payments/{id}", "payments", "/payments/{id}", "session", CUSTOMER + ADMIN),
    Route("POST", "/graphql", "graphql-gateway", "/graphql", "session", ANY, "graphql"),
)


def match(method, path):
    path_matched = False
    for route in ROUTES:
        found = route.regex.match(path)
        if found:
            path_matched = True
            if route.method == method:
                return route, found.groupdict(), True
    return None, {}, path_matched
