import grpc
import pytest

from services.analytics import analytics_pb2 as pb
from services.analytics import analytics_pb2_grpc as rpc
from tests.support.helpers import gql, pay, place_order


def canal(stack):
    channel = grpc.insecure_channel(f"127.0.0.1:{stack.ports['analytics']}")
    return rpc.AnalyticsStub(channel)


def aplanar(stream):
    return [fact for batch in stream for fact in batch.facts]


def metadata(stack, roles="admin", caller="graphql-gateway", token=None):
    token = token or stack.root.read("mariachi/edges/analytics/graphql-gateway")["token"]
    return (("x-service-caller", caller), ("x-service-token", token), ("x-user-roles", roles))


def preparar_ventas(stack):
    camila, matias = stack.client("camila"), stack.client("matias")
    pay(stack, camila, place_order(camila, [(1, 2), (4, 1)]).json())
    pay(stack, matias, place_order(matias, [(1, 1), (7, 2)]).json())
    place_order(camila, [(2, 9)])


def test_health_es_publico(stack):
    assert canal(stack).Health(pb.Empty()).status == "ok"


def test_sin_credenciales_o_sin_rol_admin_se_rechaza(stack):
    stub = canal(stack)
    with pytest.raises(grpc.RpcError) as e:
        stub.SalesSummary(pb.SummaryRequest(days=7))
    assert e.value.code() == grpc.StatusCode.PERMISSION_DENIED
    with pytest.raises(grpc.RpcError) as e:
        stub.SalesSummary(pb.SummaryRequest(days=7), metadata=metadata(stack, roles="customer"))
    assert e.value.code() == grpc.StatusCode.PERMISSION_DENIED
    with pytest.raises(grpc.RpcError) as e:
        stub.SalesSummary(pb.SummaryRequest(days=7), metadata=metadata(stack, token="falso"))
    assert e.value.code() == grpc.StatusCode.PERMISSION_DENIED
    with pytest.raises(grpc.RpcError) as e:
        stub.SalesSummary(pb.SummaryRequest(days=7), metadata=metadata(stack, caller="orders"))
    assert e.value.code() == grpc.StatusCode.PERMISSION_DENIED
    with pytest.raises(grpc.RpcError) as e:
        list(stub.StreamSales(pb.StreamRequest(), metadata=metadata(stack, roles="kitchen")))
    assert e.value.code() == grpc.StatusCode.PERMISSION_DENIED


def test_sync_es_idempotente_y_resumen_correcto(stack):
    preparar_ventas(stack)
    stub = canal(stack)
    md = metadata(stack)
    assert stub.Sync(pb.Empty(), metadata=md).imported == 4
    assert stub.Sync(pb.Empty(), metadata=md).imported == 0
    resumen = stub.SalesSummary(pb.SummaryRequest(days=7, top=2), metadata=md)
    assert resumen.orders == 2
    assert resumen.revenue == (2 * 2500 - 2500) + 4500 + 2500 + 2 * 3500
    assert [(p.product_id, p.units, p.revenue) for p in resumen.top_products] == [(7, 2, 7000), (1, 3, 5000)]


def test_ordenes_no_pagadas_no_cuentan(stack):
    preparar_ventas(stack)
    stub, md = canal(stack), metadata(stack)
    stub.Sync(pb.Empty(), metadata=md)
    productos = {p.product_id for p in stub.SalesSummary(pb.SummaryRequest(days=7, top=10), metadata=md).top_products}
    assert 2 not in productos


def test_streaming_entrega_todo_en_orden(stack):
    preparar_ventas(stack)
    stub, md = canal(stack), metadata(stack)
    stub.Sync(pb.Empty(), metadata=md)
    hechos = aplanar(stub.StreamSales(pb.StreamRequest(after_id=0, limit=0), metadata=md))
    assert len(hechos) == 4
    assert [h.id for h in hechos] == sorted(h.id for h in hechos)
    parcial = aplanar(stub.StreamSales(pb.StreamRequest(after_id=hechos[1].id, limit=0), metadata=md))
    assert [h.id for h in parcial] == [h.id for h in hechos[2:]]
    assert len(aplanar(stub.StreamSales(pb.StreamRequest(after_id=0, limit=3), metadata=md))) == 3


def test_resumen_de_ventas_via_graphql_solo_admin(stack):
    preparar_ventas(stack)
    admin, camila = stack.client("benjamin"), stack.client("camila")
    assert gql(admin, "mutation { syncAnalytics }").json()["data"]["syncAnalytics"] == 4
    r = gql(admin, "{ salesSummary(days: 7, top: 3) { orders revenue topProducts { productId name units revenue } } }").json()
    resumen = r["data"]["salesSummary"]
    assert resumen["orders"] == 2 and resumen["revenue"] == 16500
    assert [p["name"] for p in resumen["topProducts"]] == ["Nachos Supreme", "Tacos al Pastor", "Burrito Especial"]
    denegado = gql(camila, "{ salesSummary { orders } }").json()
    assert denegado.get("data") is None or denegado["data"]["salesSummary"] is None
    assert "administracion" in denegado["errors"][0]["message"].lower()


def test_analytics_caido_es_error_parcial_en_graphql(stack):
    admin = stack.client("benjamin")
    stack.stop_analytics()
    try:
        r = gql(admin, "{ me { username } salesSummary { orders } }").json()
    finally:
        stack.start_analytics()
    assert r["data"] is None or r["data"].get("me") is not None
    assert "analytics" in r["errors"][0]["message"].lower()


def test_sincronizacion_periodica_automatica(tmp_path):
    import time

    from tests.support.stack import Stack

    s = Stack(tmp_path, extra={"analytics": {"sync_interval": 0.4}}).start()
    try:
        camila = s.client("camila")
        pay(s, camila, place_order(camila, [(1, 2)]).json())
        stub = canal(s)
        md = metadata(s)
        deadline = time.time() + 10
        while time.time() < deadline:
            if stub.SalesSummary(pb.SummaryRequest(days=7), metadata=md).orders == 1:
                break
            time.sleep(0.2)
        assert stub.SalesSummary(pb.SummaryRequest(days=7), metadata=md).revenue == 2500
    finally:
        s.stop()
