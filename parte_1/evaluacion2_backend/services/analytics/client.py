import grpc

from common.logs import request_id_var
from common.topology import edge_path
from common.vault import VaultError
from services.analytics import analytics_pb2 as pb
from services.analytics import analytics_pb2_grpc as rpc


class AnalyticsUnavailable(Exception):
    pass


class AnalyticsDenied(Exception):
    pass


class AnalyticsClient:
    def __init__(self, cfg, secrets, address):
        self.cfg = cfg
        self.secrets = secrets
        self.address = address
        self._channel = None
        self._stub = None

    def _ensure(self):
        if self._channel is None:
            self._channel = grpc.aio.insecure_channel(self.address)
            self._stub = rpc.AnalyticsStub(self._channel)
        return self._stub

    def _metadata(self, user):
        try:
            edge = self.secrets.get(edge_path("analytics", self.cfg.name))
        except VaultError:
            raise AnalyticsUnavailable("Secretos no disponibles")
        return (
            ("x-service-caller", self.cfg.name),
            ("x-service-token", edge["token"]),
            ("x-user-roles", ",".join(user.roles) if user else ""),
            ("x-request-id", request_id_var.get()),
        )

    def _translate(self, error):
        if error.code() == grpc.StatusCode.PERMISSION_DENIED:
            return AnalyticsDenied(error.details())
        return AnalyticsUnavailable("Servicio analytics no disponible")

    async def summary(self, user, days=7, top=5):
        try:
            return await self._ensure().SalesSummary(
                pb.SummaryRequest(days=days, top=top), metadata=self._metadata(user), timeout=5
            )
        except grpc.aio.AioRpcError as error:
            raise self._translate(error)

    async def sync(self, user):
        try:
            return await self._ensure().Sync(pb.Empty(), metadata=self._metadata(user), timeout=30)
        except grpc.aio.AioRpcError as error:
            raise self._translate(error)

    async def stream_sales(self, user, after_id=0, limit=0):
        try:
            async for batch in self._ensure().StreamSales(
                pb.StreamRequest(after_id=after_id, limit=limit), metadata=self._metadata(user)
            ):
                for fact in batch.facts:
                    yield fact
        except grpc.aio.AioRpcError as error:
            raise self._translate(error)

    async def close(self):
        if self._channel is not None:
            await self._channel.close()
