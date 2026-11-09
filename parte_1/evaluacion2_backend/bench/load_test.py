import json
import multiprocessing
import statistics
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import grpc
import httpx
import psutil

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bench.rest_baseline import create_rest_baseline
from services.analytics import analytics_pb2 as pb
from services.analytics import analytics_pb2_grpc as rpc
from tests.support.stack import Stack, free_port

ROWS = int(sys.argv[1]) if len(sys.argv) > 1 else 100_000
PAGE = 2000


def percentile(values, p):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(len(ordered) * p))]


def seed_facts(db_path, rows):
    from common.db import Database

    db = Database(db_path)
    now = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    with db.tx() as c:
        c.executemany(
            "INSERT INTO sales_facts(order_id,product_id,name,qty,amount,at) VALUES(?,?,?,?,?,?)",
            (
                (f"ORD-{i // 3:07d}", i % 3 + 1, ("Tacos al Pastor", "Burrito Especial", "Nachos Supreme")[i % 3], 1 + i % 4, 2500 * (1 + i % 4), now)
                for i in range(rows)
            ),
        )


def fetch_rest(base):
    total_bytes, count, after = 0, 0, 0
    with httpx.Client(base_url=base, timeout=60) as http:
        while True:
            r = http.get("/sales", params={"after_id": after, "limit": PAGE})
            total_bytes += len(r.content)
            items = r.json()["items"]
            if not items:
                break
            count += len(items)
            after = items[-1]["id"]
    return count, total_bytes


def fetch_grpc(stub, md):
    total_bytes, count = 0, 0
    for batch in stub.StreamSales(pb.StreamRequest(after_id=0, limit=0), metadata=md):
        total_bytes += batch.ByteSize() + 5
        count += len(batch.facts)
    return count, total_bytes


PROC = {"p": None, "rss": 0}


def cpu_seconds():
    t = PROC["p"].cpu_times()
    return t.user + t.system


def timed(fn, *args):
    cpu = cpu_seconds()
    started = time.perf_counter()
    result = fn(*args)
    elapsed = time.perf_counter() - started
    PROC["rss"] = max(PROC["rss"], PROC["p"].memory_info().rss)
    PROC["last_cpu"] = cpu_seconds() - cpu
    return elapsed, result


def concurrent(fn, workers, per_worker):
    latencies = []

    def work():
        local = []
        for _ in range(per_worker):
            started = time.perf_counter()
            fn()
            local.append((time.perf_counter() - started) * 1000)
        return local

    started = time.perf_counter()
    with ThreadPoolExecutor(workers) as pool:
        for chunk in [f.result() for f in [pool.submit(work) for _ in range(workers)]]:
            latencies.extend(chunk)
    elapsed = time.perf_counter() - started
    return {
        "workers": workers,
        "requests": len(latencies),
        "rps": round(len(latencies) / elapsed, 1),
        "p50_ms": round(statistics.median(latencies), 1),
        "p95_ms": round(percentile(latencies, 0.95), 1),
    }


def main():
    from bench.server_proc import serve

    tmp = Path(tempfile.mkdtemp())
    results = {"rows": ROWS, "page": PAGE, "topology": "servidores en un proceso aparte, cliente en otro; loopback"}
    ctx = multiprocessing.get_context("spawn")
    parent, child = ctx.Pipe()
    ports = {"vault": free_port(), "grpc": free_port(), "rest": free_port()}
    proc = ctx.Process(target=serve, args=(str(tmp / "analytics"), ports["vault"], ports["grpc"], ports["rest"], ROWS, child))
    proc.start()
    try:
        token = parent.recv()
        PROC["p"] = psutil.Process(proc.pid)
        base = f"http://127.0.0.1:{ports['rest']}"
        md = (("x-service-caller", "graphql-gateway"), ("x-service-token", token), ("x-user-roles", "admin"))
        channel = grpc.insecure_channel(f"127.0.0.1:{ports['grpc']}")
        stub = rpc.AnalyticsStub(channel)

        fetch_rest(base)
        fetch_grpc(stub, md)
        stream = {"rest": [], "grpc": []}
        for _ in range(3):
            t, (n, b) = timed(fetch_rest, base)
            stream["rest"].append((t, n, b, PROC["last_cpu"]))
            t, (n, b) = timed(fetch_grpc, stub, md)
            stream["grpc"].append((t, n, b, PROC["last_cpu"]))
        results["export"] = {
            kind: {
                "rows": runs[0][1],
                "bytes": runs[0][2],
                "seconds_median": round(statistics.median(r[0] for r in runs), 3),
                "rows_per_second": round(runs[0][1] / statistics.median(r[0] for r in runs)),
                "server_cpu_seconds_median": round(statistics.median(r[3] for r in runs), 2),
            }
            for kind, runs in stream.items()
        }
        results["export"]["bytes_ratio_grpc_vs_rest"] = round(results["export"]["grpc"]["bytes"] / results["export"]["rest"]["bytes"], 3)
        results["export"]["speedup_grpc_vs_rest"] = round(results["export"]["rest"]["seconds_median"] / results["export"]["grpc"]["seconds_median"], 2)

        http = httpx.Client(base_url=base, timeout=60)
        summary = {"rest": [], "grpc": []}
        for workers in (1, 8, 32):
            summary["rest"].append(concurrent(lambda: http.get("/summary", params={"days": 7, "top": 5}).json(), workers, 20))
            summary["grpc"].append(concurrent(lambda: stub.SalesSummary(pb.SummaryRequest(days=7, top=5), metadata=md), workers, 20))
        results["summary"] = summary
        results["server_rss_mb_max"] = round(PROC["rss"] / 1e6)
        results["environment"] = {"cpus": psutil.cpu_count(), "ram_mb": round(psutil.virtual_memory().total / 1e6), "python": sys.version.split()[0], "grpcio": grpc.__version__}
    finally:
        parent.send("stop")
        proc.join(timeout=20)
        if proc.is_alive():
            proc.terminate()

    stack = Stack(tmp / "stack", extra={"api-gateway": {"limits": {"login": (10000, 60), "default": (10**7, 60)}}}).start()
    try:
        gateway = stack.client("camila")
        crud = []
        for workers in (1, 8, 32):
            crud.append(concurrent(lambda: gateway.get("/products", params={"limit": 20}).raise_for_status(), workers, 15))
        results["crud_products_via_gateway"] = crud
        results["crud_topology"] = "stack completo en un solo proceso (limite del banco de pruebas)"
    finally:
        stack.stop()
    out = Path(__file__).with_name("results.json")
    out.write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
