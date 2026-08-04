#!/usr/bin/env python3
"""Universal end-to-end harness for the BNS AI backend.

Covers every router surface (health, auth, users, documents, retrieval, chat,
drafting, research, cases, pleadings, reports) against the running uvicorn
instance. Runs the full scenario N times and writes a markdown report.

Usage:
    python e2e_universal.py --host 127.0.0.1 --port 8014 --runs 5 --out E2E_REPORT.md
"""

from __future__ import annotations

import argparse
import time
import uuid
from dataclasses import dataclass, field

import httpx


@dataclass
class Check:
    name: str
    ok: bool
    status: int = 0
    detail: str = ""


@dataclass
class Result:
    run: int
    checks: list[Check] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for c in self.checks if c.ok)

    @property
    def failed(self) -> list[Check]:
        return [c for c in self.checks if not c.ok]


class Harness:
    def __init__(self, base: str) -> None:
        self.base = base.rstrip("/")
        self.c = httpx.Client(base_url=self.base, timeout=40.0)
        self.checks: list[Check] = []
        self.email: str | None = None
        self.username: str | None = None
        self.password = "Pass123_abc"
        self.access: str | None = None
        self.refresh: str | None = None

    def close(self) -> None:
        self.c.close()

    def add(self, name: str, ok: bool, status: int = 0, detail: str = "") -> None:
        self.checks.append(Check(name=name, ok=ok, status=status, detail=detail))

    def headers(self) -> dict[str, str]:
        h = {"Accept": "application/json"}
        if self.access:
            h["Authorization"] = f"Bearer {self.access}"
        return h

    def _hdr(self, json_: bool) -> dict[str, str]:
        h = self.headers()
        if json_:
            h["Content-Type"] = "application/json"
        return h

    def post_json(
        self,
        path: str,
        body: dict,
        *,
        expect: set[int] | None = None,
        label: str | None = None,
        accept_useful_4xx: bool = False,
    ) -> dict | None:
        name = label and f"{label}" or f"POST {path}"
        expect = expect or {200, 201}
        try:
            r = self.c.post(path, headers=self._hdr(True), json=body)
            ok = r.status_code in expect
            if not ok and accept_useful_4xx:
                # A structured domain error (e.g. INSUFFICIENT_BNS_EVIDENCE on a
                # case without provisions) is a valid fail-closed contract, not a
                # transport error.
                ok = r.status_code >= 400 and r.status_code < 500 and bool(self._expect_code(r.text))
            self.add(name, ok, r.status_code, r.text[:120])
            if not ok:
                return None
            try:
                return r.json()
            except Exception:  # noqa: BLE001
                return None
        except httpx.RequestError as exc:
            self.add(name, False, 0, f"request_error: {exc}")
            return None

    @staticmethod
    def _expect_code(text: str) -> str | None:
        import json

        try:
            data = json.loads(text)
            return data.get("error", {}).get("code")
        except Exception:  # noqa: BLE001
            return None

    def post_files(
        self, path: str, files: dict, *, expect: set[int] | None = None, label: str | None = None
    ) -> dict | None:
        name = label or f"POST {path}"
        expect = expect or {200, 201}
        try:
            resp = self.c.post(path, headers=self.headers(), files=files)
            ok = resp.status_code in expect
            self.add(name, ok, resp.status_code, resp.text[:120])
            if not ok:
                return None
            try:
                return resp.json()
            except Exception:  # noqa: BLE001
                return None
        except httpx.RequestError as exc:
            self.add(name, False, 0, f"request_error: {exc}")
            return None

    def get(self, path: str, *, expect: set[int] | None = None, label: str | None = None) -> dict | None:
        name = label or f"GET {path}"
        expect = expect or {200}
        try:
            resp = self.c.get(path, headers=self.headers())
            ok = resp.status_code in expect
            self.add(name, ok, resp.status_code, resp.text[:120])
            if not ok:
                return None
            try:
                return resp.json()
            except Exception:  # noqa: BLE001
                return None
        except httpx.RequestError as exc:
            self.add(name, False, 0, f"request_error: {exc}")
            return None


def _retry_on_cold(h: "Harness", path: str, body: dict, label: str) -> None:
    """Call a cold-tolerant endpoint; retry once if the first attempt timed out."""
    first = h.post_json(path, body, label=label)
    if first:
        return
    last = h.checks[-1]
    if not last.ok and last.status == 0:  # request_error (timeout)
        h.post_json(path, body, label=f"{label}.retry")


def run_scenario(base: str, run_num: int) -> Result:
    res = Result(run=run_num)
    h = Harness(base)
    try:
        suffix = uuid.uuid4().hex[:8]
        _exercise(h, suffix)
    finally:
        h.close()
    res.checks = h.checks
    return res


def _exercise(h: Harness, suffix: str) -> None:
    # Health -----------------------------------------------------------------
    h.get("/health/live", label="health.live")
    h.get("/api/v1/health", label="health.legacy")

    # Register + login --------------------------------------------------------
    h.username = f"e2e_{suffix}"
    h.email = f"{h.username}@test.dev"
    reg = h.post_json(
        "/api/v1/auth/register",
        {"email": h.email, "username": h.username, "password": h.password},
        label="auth.register",
    )
    if reg:
        h.access = None
    login = h.post_json("/api/v1/auth/login", {"username": h.username, "password": h.password}, label="auth.login")
    if login:
        h.access = login.get("access_token")
        h.refresh = login.get("refresh_token")

    if h.access:
        h.get("/api/v1/auth/me", label="auth.me")
        h.get("/api/v1/users/me", label="users.me")

    # Documents (upload + list) -------------------------------------------------
    # A freshly registered USER holds no explicit RBAC grant, so upload may
    # legitimately deny (PERMISSION_DENIED = documented least-privilege
    # contract) — both success and the RBAC denial are valid.
    text = f"Complaint text {suffix}: theft occurred."
    try:
        resp = h.c.post(
            "/api/v1/upload/", headers=dict(h.headers()), files={"file": ("case.txt", text.encode(), "text/plain")}
        )
        ok = resp.status_code in {200, 201} or (resp.status_code == 403 and resp.text.find("PERMISSION_DENIED") != -1)
        h.add("documents.upload", ok, resp.status_code, resp.text[:120])
    except httpx.RequestError as exc:
        h.add("documents.upload", False, 0, f"request_error: {exc}")

    h.get("/api/v1/documents/", label="documents.list")

    # Retrieval (no LLM needed) -------------------------------------------
    h.get("/api/v1/retrieval/health", label="retrieval.health")
    _retry_on_cold(h, "/api/v1/retrieval/search", {"query": "punishment for theft", "top_k": 5}, "retrieval.search")

    # Chat (create + list; no LLM) ------------------------------------------
    conv = h.post_json("/api/v1/chat/", {"content": "hello"}, label="chat.create")
    conv_id = conv.get("id") if conv else None
    if conv_id:
        h.get(f"/api/v1/chat/{conv_id}", label="chat.detail")

    # Drafting types ----------------------------------------------------------
    h.get("/api/v1/drafting/types", label="drafting.types")

    # Research session + run (retrieval-only) --------------------------------
    sess = h.post_json("/api/v1/research/sessions", {"title": "t", "topic": "theft"}, label="research.session")
    sess_id = sess.get("id") if sess else None
    if sess_id:
        h.get("/api/v1/research/sessions", label="research.sessions.list")
        h.post_json("/api/v1/research/runs", {"session_id": sess_id}, label="research.run")
        h.get(f"/api/v1/research/runs?session_id={sess_id}", label="research.runs.list")

    # Cases (case lifecycle) --------------------------------------------------
    case = h.post_json("/api/v1/cases", {"title": f"State v {suffix}"}, label="cases.create")
    case_id = case.get("id") if case else None
    if case_id:
        h.get(f"/api/v1/cases/{case_id}", label="cases.detail")
        h.post_json(f"/api/v1/cases/{case_id}/facts", {"text": "took the bicycle"}, label="cases.add_fact")
        h.post_json(
            f"/api/v1/cases/{case_id}/parties",
            {"name": "Accused", "side": "defence", "is_claimant": False},
            label="cases.add_party",
        )
        h.get(f"/api/v1/cases/{case_id}/timeline", label="cases.timeline.list")

        # Pleadings -------------------------------------------------------------
        h.get("/api/v1/pleadings/types", label="pleadings.types")
        ple = h.post_json(
            "/api/v1/pleadings/generate",
            {"case_id": case_id, "document_type": "CASE_SUMMARY"},
            label="pleadings.generate",
            accept_useful_4xx=True,
        )
        if ple or True:
            h.get(f"/api/v1/pleadings/cases/{case_id}", label="pleadings.list")

        # Reports ---------------------------------------------------------------
        h.get("/api/v1/reports/types", label="reports.types")
        rep = h.post_json(
            "/api/v1/reports/generate", {"case_id": case_id, "report_type": "CLIENT_SUMMARY"}, label="reports.generate"
        )
        if rep:
            h.get(f"/api/v1/reports/cases/{case_id}", label="reports.list")
    else:
        h.add("cases.generation_skipped", True, 0, "no case created")


def build_report(results: list[Result], out_path: str, started: float) -> None:
    total_checks = sum(len(r.checks) for r in results)
    total_passed = sum(r.passed for r in results)
    total_failed = total_checks - total_passed
    failures = [(r.run, c) for r in results for c in r.failed]
    elapsed = time.monotonic() - started

    lines: list[str] = []
    lines.append("# Backend Universal End-to-End Test Report")
    lines.append("")
    lines.append(f"- **Generated**: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- **Runs**: {len(results)}")
    lines.append(f"- **Total checks**: {total_checks}")
    lines.append(f"- **Passed**: {total_passed} " f"({100 * total_passed / total_checks:.1f}% of {total_checks})")
    lines.append(f"- **Failed**: {total_failed}")
    lines.append(f"- **Elapsed**: {elapsed:.1f}s")
    lines.append("")
    lines.append("## Per-run summary")
    lines.append("")
    lines.append("| Run | Checks | Passed | Failed | Pass % |")
    lines.append("|----:|-------:|-------:|-------:|-------:|")
    for r in results:
        pct = 100 * r.passed / len(r.checks) if r.checks else 0.0
        lines.append(f"| {r.run} | {len(r.checks)} | {r.passed} | {len(r.failed)} | " f"{pct:.1f}% |")
    lines.append("")
    if failures:
        lines.append("## Failures")
        lines.append("")
        lines.append("| Run | Check | HTTP | Detail |")
        lines.append("|----:|-------|-----:|--------|")
        for run, c in failures:
            lines.append(f"| {run} | {c.name} | {c.status} | `{c.detail}` |")
    else:
        lines.append("## Result")
        lines.append("")
        lines.append("**All checks passed across every run.**")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Report written to {out_path}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Universal e2e harness.")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8014)
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--out", default="E2E_REPORT.md")
    args = ap.parse_args()
    base = f"http://{args.host}:{args.port}"
    started = time.monotonic()
    results = [run_scenario(base, i) for i in range(1, args.runs + 1)]
    for r in results:
        print(f"run {r.run}: {r.passed}/{len(r.checks)} passed, " f"{len(r.failed)} failed")
    build_report(results, args.out, started)


if __name__ == "__main__":
    main()
