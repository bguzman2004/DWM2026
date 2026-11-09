from fastapi import Depends, HTTPException, Request
from graphql import NoSchemaIntrospectionCustomRule
from strawberry import Schema
from strawberry.exceptions import StrawberryGraphQLError
from strawberry.extensions import AddValidationRules, MaskErrors, QueryDepthLimiter
from strawberry.fastapi import GraphQLRouter
from strawberry.dataloader import DataLoader
from strawberry.fastapi import BaseContext

from common.app import create_service_app
from common.calls import ServiceClient, UpstreamTimeout, UpstreamUnavailable, SecretsUnavailable, raise_for_upstream
from common.config import Settings
from common.logs import log
from common.security import make_guard, require_user
from common.vault import make_secrets
from services.analytics.client import AnalyticsClient, AnalyticsDenied, AnalyticsUnavailable
from services.graphql_gateway.limits import cost_limit
from services.graphql_gateway.schema import Mutation, Query, UserError

MAX_DEPTH = 6
MAX_COST = 5000

SAFE_ERRORS = (
    UserError, UpstreamUnavailable, UpstreamTimeout, SecretsUnavailable, AnalyticsUnavailable, AnalyticsDenied,
    PermissionError, HTTPException, StrawberryGraphQLError,
)


def should_mask(error):
    current = getattr(error, "original_error", None)
    if current is None:
        return False
    while current is not None:
        if isinstance(current, SAFE_ERRORS):
            return False
        current = getattr(current, "original_error", None)
    return True


class QuietSchema(Schema):
    def process_errors(self, errors, execution_context=None):
        for error in errors:
            original = getattr(error, "original_error", None)
            log(
                "graphql-gateway",
                "graphql_error",
                level=30,
                path=".".join(str(p) for p in (error.path or [])) or "-",
                error=type(original).__name__ if original is not None else "GraphQLError",
            )


def build_schema(introspection, max_depth=MAX_DEPTH, max_cost=MAX_COST):
    rules = [cost_limit(max_cost)]
    if not introspection:
        rules.append(NoSchemaIntrospectionCustomRule)
    return QuietSchema(
        query=Query,
        mutation=Mutation,
        extensions=[
            QueryDepthLimiter(max_depth=max_depth),
            AddValidationRules(rules),
            MaskErrors(should_mask_error=should_mask),
        ],
    )


class Context(BaseContext):
    def __init__(self, user, clients, analytics):
        super().__init__()
        self.user = user
        self._clients = clients
        self.analytics = analytics
        self.products = DataLoader(self._load_products)
        self.clients = DataLoader(self._load_clients)
        self.payments = DataLoader(self._load_payments)

    async def call(self, callee, method, path, **kwargs):
        return await self._clients[callee].request(method, path, user=self.user, **kwargs)

    async def _load_products(self, keys):
        response = await self.call("inventory", "GET", "/products/batch", params={"ids": ",".join(str(k) for k in keys)})
        raise_for_upstream(response)
        by_id = {p["id"]: p for p in response.json()["items"]}
        return [by_id.get(k) for k in keys]

    async def _load_clients(self, keys):
        response = await self.call("clients", "GET", "/clients/batch", params={"ids": ",".join(keys)})
        raise_for_upstream(response)
        by_id = {c["id"]: c for c in response.json()["items"]}
        return [by_id.get(k) for k in keys]

    async def _load_payments(self, keys):
        response = await self.call("payments", "GET", "/payments", params={"order_ids": ",".join(keys)})
        raise_for_upstream(response)
        by_order = {}
        for payment in response.json()["items"]:
            current = by_order.get(payment["order_id"])
            if current is None or payment["status"] == "succeeded":
                by_order[payment["order_id"]] = payment
        return [by_order.get(k) for k in keys]


def create_app(cfg=None):
    cfg = cfg or Settings.from_env("graphql-gateway")
    secrets = make_secrets(cfg)
    app = create_service_app(cfg, secrets, None)
    guard = make_guard(cfg, secrets)
    clients = {name: ServiceClient(cfg, secrets, name) for name in ("orders", "inventory", "clients", "payments")}
    analytics = AnalyticsClient(cfg, secrets, cfg.extra.get("analytics_addr", ""))
    app.state.closers.extend([c.close for c in clients.values()] + [analytics.close])

    async def get_context(request: Request, caller=Depends(guard("api-gateway"))):
        user = require_user(caller)
        return Context(user, clients, analytics)

    router = GraphQLRouter(
        build_schema(
            cfg.extra.get("introspection", False),
            int(cfg.extra.get("max_depth", MAX_DEPTH)),
            int(cfg.extra.get("max_cost", MAX_COST)),
        ),
        context_getter=get_context,
        graphql_ide=None,
        allow_queries_via_get=False,
    )
    app.include_router(router, prefix="/graphql")
    return app
