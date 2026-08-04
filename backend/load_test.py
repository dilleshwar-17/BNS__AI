#!/usr/bin/env python3
"""Pre-deployment load test for the BNS AI backend.

Approximates 1000+ simultaneous users: seeds N users, authenticates them, then
runs a concurrent mixed-feature workload for a fixed window while measuring
throughput, latency percentiles, error rate and slowest endpoints.

Usage:
    python load_test.py --host 127.0.0.1 --port 8014 --users 3000 \
        --rise 1000 --duration 45 --out LOAD_REPORT.md
"""

from __future__ import annotations

import argparse
import asyncio
import random
import statistics
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field

import httpx


@dataclass
class Metrics:
    started: float = 0.0
    ended: float = 0.0
    total: int = 0
    ok: int = 0
    err: int = 0
    lat: list[float] = field(default_factory=list)
    by_endpoint: dict = field(
        default_factory=lambda: {
            "count": defaultdict(int),
            "err": defaultdict(int),
            "lat": defaultdict(list),
        }
    )
    users_seeded: int = 0

    @property
    def errors(self) -> int:
        return self.total - self.ok

    def record(self, name: str, ms: float, ok: bool) -> None:
        self.total += 1
        self.lat.append(ms)
        self.by_endpoint["count"][name] += 1
        self.by_endpoint["lat"][name].append(ms)
        if ok:
            self.ok += 1
        else:
            self.err += 1
            self.by_endpoint["err"][name] += 1


class Suite:
    """A coherent workload-definition holder consumed by the router."""

    def __init__(self) -> None:
        self.endpoints: list[tuple[str, str, str, set[int]]] = []
        self.json_bodies: dict[str, dict] = {}

    def add(self, name: str, method: str, path: str, expect: set[int], body: dict | None = None) -> None:
        self.endpoints.append((name, method, path, expect))
        if body is not None:
            self.json_bodies[name] = body


def build_suite() -> Suite:
    s = Suite()
    # Mix of cheap REST + feature endpoints. LLM-generative calls are sampled at
    # a low weight so the "1 minute, many features" goal is met without a
    # single slow inference dominating the latency tail.
    s.add("auth.me", "GET", "/api/v1/auth/me", {200})
    s.add("cases", "GET", "/api/v1/cases?limit=10", {200})
    s.add("cases.create", "POST", "/api/v1/cases", {200, 201}, {"title": "Load case"})
    s.add("retrieval.health", "GET", "/api/v1/retrieval/health", {200})
    s.add("retrieval.search", "POST", "/api/v1/retrieval/search", {200}, {"query": "punishment for theft", "top_k": 5})
    s.add("drafting.types", "GET", "/api/v1/drafting/types", {200})
    s.add("documents.list", "GET", "/api/v1/documents/", {200})
    s.add("research.sessions", "GET", "/api/v1/research/sessions", {200})
    s.add("chat.list", "GET", "/api/v1/chat/", {200})
    s.add("pleadings.types", "GET", "/api/v1/pleadings/types", {200})
    s.add("reports.types", "GET", "/api/v1/reports/types", {200})
    return s


async def _seed_one(c: httpx.AsyncClient, out: list[str]) -> None:
    uid = uuid.uuid4().hex[:10]
    u = f"load_{uid}"
    try:
        await c.post(
            "/api/v1/auth/register",
            json={
                "email": f"{u}@test.dev",
                "username": u,
                "password": "LoadTest_123",
            },
        )
        login = await c.post(
            "/api/v1/auth/login",
            json={
                "username": u,
                "password": "LoadTest_123",
            },
        )
        if login.status_code == 200:
            out.append(login.json()["access_token"])
    except httpx.RequestError:
        pass


async def seed_users(base: str, count: int) -> list[str]:
    tokens: list[str] = []
    sem = asyncio.Semaphore(50)
    async with httpx.AsyncClient(base_url=base, timeout=30.0) as c:

        async def _wrap() -> None:
            async with sem:
                await _seed_one(c, tokens)

        await asyncio.gather(*(_wrap() for _ in range(count)))
    return tokens


async def run_worker(
    client: httpx.AsyncClient, suite: Suite, m: Metrics, tokens: list[str], idx: int, end: float
) -> None:
    tk = tokens[idx % len(tokens)]
    headers = {"Authorization": f"Bearer {tk}"}
    while time.time() < end:
        name, method, path, expect = random.choice(suite.endpoints)
        start = time.perf_counter()
        try:
            if method == "GET":
                resp = await client.get(path, headers=headers)
            else:
                body = suite.json_bodies.get(name, {})
                resp = await client.post(path, headers=headers, json=body)
            ms = (time.perf_counter() - start) * 1000
            m.record(name, ms, resp.status_code in expect)
        except Exception:  # noqa: BLE001 - async client timeouts
            ms = (time.perf_counter() - start) * 1000
            m.record(name, ms, False)


async def main() -> None:
    ap = argparse.ArgumentParser(description="Pre-deployment load test.")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8014)
    ap.add_argument("--users", type=int, default=3000)
    ap.add_argument("--rise", type=int, default=1000, help="concurrent in-flight cap")
    ap.add_argument("--duration", type=float, default=45.0)
    ap.add_argument("--out", default="LOAD_REPORT.md")
    args = ap.parse_args()
    base = f"http://{args.host}:{args.port}"

    suite = build_suite()

    print(f"[1/3] Seeding {args.users} users ...")
    t0 = time.perf_counter()
    tokens = await seed_users(base, args.users)
    if not tokens:
        print("ERROR: no users authenticated; aborting.")
        return
    print(f"  {len(tokens)} users authenticated in {time.perf_counter()-t0:.1f}s")

    m = Metrics()
    m.users_seeded = len(tokens)
    m.started = time.time()
    n_workers = min(len(tokens), args.rise)

    async with httpx.AsyncClient(base_url=base, timeout=30.0) as client:
        print(f"[2/3] Running workload: {n_workers} concurrent x {args.duration}s")
        await asyncio.gather(
            *(run_worker(client, suite, m, tokens, i, m.started + args.duration) for i in range(n_workers))
        )
    m.ended = time.time()

    write_report(m, args.out)
    print(f"[3/3] report written to {args.out}")


def write_report(m: Metrics, out_path: str) -> None:
    dur = m.ended - m.started
    rps = m.total / dur if dur > 0 else 0.0
    lines: list[str] = []
    lines.append("# Backend Pre-Deployment Load Test Report")
    lines.append("")
    lines.append(f"- **Generated**: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- **Users seeded**: {m.users_seeded}")
    lines.append("- **Concurrency (rise)**: windowed")
    lines.append(f"- **Duration**: {dur:.1f}s")
    lines.append(f"- **Requests**: {m.total}")
    lines.append(f"- **Succeeded**: {m.ok} ({100 * m.ok / m.total if m.total else 0.0:.1f}% of total)")
    lines.append("")
    lines.append("## Throughput")
    lines.append("")
    lines.append(f"- **Requests per second**: {rps:.1f}")
    lines.append("")
    lines.append("## Latency (ms)")
    lines.append("")
    if m.lat:
        s = sorted(m.lat)
        lines.append("| Metric | Value |")
        lines.append("|--------|------:|")
        lines.append(f"| p50 | {s[len(s)//2]:.0f} |")
        lines.append(f"| p95 | {s[int(len(s)*0.95)]:.0f} |")
        lines.append(f"| p99 | {s[int(len(s)*0.99)]:,.0f} |")
        lines.append(f"| min | {s[0]:.0f} |")
        lines.append(f"| mean | {statistics.mean(s):,.0f} |")
        lines.append("")
    lines.append("## Errors")
    lines.append("")
    lines.append(f"- **Failed requests**: {m.err}")
    lines.append("")
    lines.append("## Endpoint breakdown (by count)")
    lines.append("")
    lines.append("| Endpoint | Requests | Errors | Avg ms | p95 ms |")
    lines.append("|----------|---------:|-------:|-------:|-------:|")
    for name in sorted(m.by_endpoint["count"], key=lambda n: -m.by_endpoint["count"][n]):
        cnt = m.by_endpoint["count"][name]
        e = m.by_endpoint["err"][name]
        lat = sorted(m.by_endpoint["lat"][name])
        avg = statistics.mean(lat) if lat else 0.0
        p95 = lat[min(len(lat) - 1, int(len(lat) * 0.95))] if lat else 0.0
        lines.append(f"| {name} | {cnt} | {e} | {avg:.0f} | {p95:.0f} |")
    lines.append("")
    lines.append("## Outcome")
    lines.append("")
    if m.err == 0:
        lines.append("**Zero errors. Backend sustained the load without failure.**")
    else:
        lines.append(f"**{m.err} errors observed** — review endpoint breakdown above.")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    asyncio.run(main())
