import base64
from typing import Optional

import strawberry
from strawberry.permission import BasePermission
from strawberry.types import Info

from common.calls import raise_for_upstream
from services.graphql_gateway.limits import MAX_PAGE


class UserError(Exception):
    pass


def encode_cursor(offset):
    return base64.urlsafe_b64encode(str(offset).encode()).decode()


def decode_cursor(cursor):
    if not cursor:
        return 0
    try:
        value = int(base64.urlsafe_b64decode(cursor.encode()).decode())
    except Exception:
        raise UserError("Cursor invalido")
    if value < 0:
        raise UserError("Cursor invalido")
    return value


def check_first(first):
    if first < 1 or first > MAX_PAGE:
        raise UserError(f"first debe estar entre 1 y {MAX_PAGE}")


class IsStaff(BasePermission):
    message = "Solo personal de cocina o administracion"

    def has_permission(self, source, info: Info, **kwargs) -> bool:
        return info.context.user.has("kitchen", "admin")


class IsAdmin(BasePermission):
    message = "Solo administracion"

    def has_permission(self, source, info: Info, **kwargs) -> bool:
        return info.context.user.has("admin")


class CanPay(BasePermission):
    message = "Solo el cliente o administracion pueden ver pagos"

    def has_permission(self, source, info: Info, **kwargs) -> bool:
        return info.context.user.has("customer", "admin")


class OwnerOrAdmin(BasePermission):
    message = "Dato privado del cliente"

    def has_permission(self, source, info: Info, **kwargs) -> bool:
        user = info.context.user
        return user.has("admin") or (bool(user.client_id) and user.client_id == source.id)


@strawberry.type
class StockInfo:
    on_hand: int
    reserved: int
    available: int


@strawberry.type
class Product:
    id: int
    name: str
    category: str
    price: int
    in_stock: bool
    raw: strawberry.Private[dict]

    @strawberry.field(permission_classes=[IsStaff])
    def stock(self) -> Optional[StockInfo]:
        if "on_hand" not in self.raw:
            return None
        return StockInfo(on_hand=self.raw["on_hand"], reserved=self.raw["reserved"], available=self.raw["available"])

    @staticmethod
    def build(raw):
        return Product(id=raw["id"], name=raw["name"], category=raw["category"], price=raw["price"], in_stock=raw["in_stock"], raw=raw)


@strawberry.type
class Client:
    id: str
    name: str
    raw: strawberry.Private[dict]

    @strawberry.field(permission_classes=[OwnerOrAdmin])
    def email(self) -> Optional[str]:
        return self.raw.get("email")

    @strawberry.field(permission_classes=[OwnerOrAdmin])
    def phone(self) -> Optional[str]:
        return self.raw.get("phone")

    @staticmethod
    def build(raw):
        return Client(id=raw["id"], name=raw["name"], raw=raw)


@strawberry.type
class Payment:
    id: str
    status: str
    amount: int
    provider_ref: str


@strawberry.type
class OrderItem:
    product_id: int
    name: str
    unit_price: int
    qty: int
    discount: int
    promo: Optional[str]

    @strawberry.field
    async def product(self, info: Info) -> Optional[Product]:
        raw = await info.context.products.load(self.product_id)
        return Product.build(raw) if raw else None


@strawberry.type
class Order:
    id: str
    status: str
    subtotal: int
    discount: int
    total: int
    created_at: str
    notes: Optional[str]
    client_id: strawberry.Private[str]
    lines: strawberry.Private[list]

    @strawberry.field
    def items(self) -> list[OrderItem]:
        return [OrderItem(**line) for line in self.lines]

    @strawberry.field
    async def client(self, info: Info) -> Optional[Client]:
        raw = await info.context.clients.load(self.client_id)
        return Client.build(raw) if raw else None

    @strawberry.field(permission_classes=[CanPay])
    async def payment(self, info: Info) -> Optional[Payment]:
        raw = await info.context.payments.load(self.id)
        if not raw:
            return None
        return Payment(id=raw["id"], status=raw["status"], amount=raw["amount"], provider_ref=raw["provider_ref"])

    @staticmethod
    def build(raw):
        return Order(
            id=raw["id"], status=raw["status"], subtotal=raw["subtotal"], discount=raw["discount"], total=raw["total"], created_at=raw["created_at"], notes=raw.get("notes"),
            client_id=raw["client_id"], lines=raw["items"],
        )


@strawberry.type
class OrderPage:
    nodes: list[Order]
    total: int
    next_cursor: Optional[str]


@strawberry.type
class ProductPage:
    nodes: list[Product]
    total: int
    next_cursor: Optional[str]


@strawberry.type
class ProductTotal:
    product_id: int
    name: str
    units: int
    revenue: int


@strawberry.type
class SalesSummary:
    orders: int
    revenue: int
    top_products: list[ProductTotal]


@strawberry.type
class Me:
    user_id: str
    username: str
    roles: list[str]
    client_id: Optional[str]

    @strawberry.field
    async def client(self, info: Info) -> Optional[Client]:
        if not self.client_id:
            return None
        raw = await info.context.clients.load(self.client_id)
        return Client.build(raw) if raw else None


@strawberry.input
class ItemInput:
    product_id: int
    qty: int


@strawberry.type
class Query:
    @strawberry.field
    def me(self, info: Info) -> Me:
        user = info.context.user
        return Me(user_id=user.user_id, username=user.username, roles=list(user.roles), client_id=user.client_id or None)

    @strawberry.field
    async def products(self, info: Info, first: int = 20, after: Optional[str] = None, category: Optional[str] = None) -> ProductPage:
        check_first(first)
        offset = decode_cursor(after)
        params = {"limit": first, "offset": offset}
        if category:
            params["category"] = category
        response = await info.context.call("inventory", "GET", "/products", params=params)
        raise_for_upstream(response)
        body = response.json()
        more = offset + first < body["total"]
        return ProductPage(
            nodes=[Product.build(p) for p in body["items"]], total=body["total"],
            next_cursor=encode_cursor(offset + first) if more else None,
        )

    @strawberry.field
    async def product(self, info: Info, id: int) -> Optional[Product]:
        raw = await info.context.products.load(id)
        return Product.build(raw) if raw else None

    @strawberry.field
    async def my_orders(self, info: Info, first: int = 20, after: Optional[str] = None, status: Optional[str] = None) -> OrderPage:
        check_first(first)
        offset = decode_cursor(after)
        params = {"limit": first, "offset": offset}
        if status:
            params["status"] = status
        response = await info.context.call("orders", "GET", "/orders", params=params)
        raise_for_upstream(response)
        body = response.json()
        more = offset + first < body["total"]
        return OrderPage(
            nodes=[Order.build(o) for o in body["items"]], total=body["total"],
            next_cursor=encode_cursor(offset + first) if more else None,
        )

    @strawberry.field
    async def order(self, info: Info, id: str) -> Optional[Order]:
        response = await info.context.call("orders", "GET", f"/orders/{id}")
        if response.status_code == 404:
            return None
        raise_for_upstream(response)
        return Order.build(response.json())

    @strawberry.field(permission_classes=[IsAdmin])
    async def sales_summary(self, info: Info, days: int = 7, top: int = 5) -> SalesSummary:
        reply = await info.context.analytics.summary(info.context.user, days=days, top=top)
        return SalesSummary(
            orders=reply.orders,
            revenue=reply.revenue,
            top_products=[
                ProductTotal(product_id=p.product_id, name=p.name, units=p.units, revenue=p.revenue)
                for p in reply.top_products
            ],
        )


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_order(
        self, info: Info, items: list[ItemInput], notes: Optional[str] = None, idempotency_key: Optional[str] = None
    ) -> Order:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else None
        response = await info.context.call(
            "orders", "POST", "/orders", json={"items": [{"product_id": i.product_id, "qty": i.qty} for i in items], "notes": notes}, headers=headers
        )
        raise_for_upstream(response)
        return Order.build(response.json())

    @strawberry.mutation(permission_classes=[IsAdmin])
    async def sync_analytics(self, info: Info) -> int:
        reply = await info.context.analytics.sync(info.context.user)
        return reply.imported
