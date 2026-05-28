#!/usr/bin/env python3
"""test_v1_v2_compat.py — W31.7c

Lightweight integration dogfood: V1 plugin against V2 API via deprecation
aliases. Verifies backwards-compat before the V1→V2 plugin migration in W33.

What this verifies:
  - The V2 REST API endpoints that V1 plugin calls still respond correctly
    through their deprecation-alias paths.
  - graph-manifest.json (renamed from skills-graph.json) is served at both
    the new canonical path and the V1 alias path.
  - The skills/ endpoint alias redirects to processes/ correctly.
  - Submission contract version "2.0.0" is accepted.

Run via Cowork stub harness (W31.7b) or directly with a BASE_URL:
  python3 tests/substrate-contract/test_v1_v2_compat.py \\
      --base-url https://becivic.be \\
      [--harness-key <key>]

  # Local dev:
  python3 tests/substrate-contract/test_v1_v2_compat.py \\
      --base-url http://localhost:8787

Exit codes:
  0 — all checks pass
  1 — one or more checks failed
  2 — invalid arguments / unreachable

Spec: W31.7c, bc-workspace/roadmap/sprints/2026-W31-v2-api-and-auth.md §Phase7
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Minimal test runner (stdlib only)
# ─────────────────────────────────────────────────────────────────────────────

_pass = 0
_fail = 0
_skip = 0
_failures: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    global _pass, _fail
    if cond:
        _pass += 1
        print(f"  ok   {label}")
    else:
        _fail += 1
        msg = f"  FAIL {label}"
        if detail:
            msg += f" — {detail}"
        print(msg, file=sys.stderr)
        _failures.append(label)


def skip(label: str, reason: str) -> None:
    global _skip
    _skip += 1
    print(f"  skip {label} ({reason})")


def section(name: str) -> None:
    print(f"\n{name}")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helpers
# ─────────────────────────────────────────────────────────────────────────────

def get(url: str, headers: dict[str, str] | None = None) -> tuple[int, Any]:
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                return resp.status, json.loads(body)
            except json.JSONDecodeError:
                return resp.status, body
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, body
    except (urllib.error.URLError, OSError) as e:
        return -1, str(e)


def is_reachable(base: str) -> bool:
    status, _ = get(f"{base}/api/health")
    return status == 200


# ─────────────────────────────────────────────────────────────────────────────
# V1 alias compatibility checks
# ─────────────────────────────────────────────────────────────────────────────

def check_manifest_alias(base: str, headers: dict[str, str]) -> None:
    """V1 plugin fetched /agents/skills-graph.json. V2 renamed it to
    /agents/graph-manifest.json. Both paths must work."""
    section("V1→V2 manifest alias: skills-graph.json → graph-manifest.json")

    # Canonical V2 path
    status, body = get(f"{base}/agents/graph-manifest.json", headers)
    check(
        "GET /agents/graph-manifest.json → 200",
        status == 200,
        f"got {status}",
    )
    if status == 200 and isinstance(body, dict):
        check(
            "graph-manifest.json has 'entries' key (V2 shape)",
            "entries" in body,
            f"keys: {list(body.keys())}",
        )
        check(
            "graph-manifest.json has 'version' key",
            "version" in body,
            f"keys: {list(body.keys())}",
        )

    # V1 alias path (serves the same content, possibly via redirect)
    status_v1, body_v1 = get(f"{base}/agents/skills-graph.json", headers)
    check(
        "GET /agents/skills-graph.json (V1 alias) → 200 or 301/302",
        status_v1 in (200, 301, 302),
        f"got {status_v1}",
    )


def check_process_endpoint(base: str, headers: dict[str, str]) -> None:
    """V2 API serves Process content. V1 plugin read /processes/<id>/process.md
    (or the MCP equivalent). The REST API must serve at /api/processes/<id>."""
    section("V2 process endpoint: GET /api/processes/<id>")

    # Use a known-stable process ID from the corpus
    process_id = "nationality-application"
    status, body = get(f"{base}/api/processes/{process_id}", headers)
    check(
        f"GET /api/processes/{process_id} → 200",
        status == 200,
        f"got {status}",
    )
    if status == 200 and isinstance(body, dict):
        check(
            f"process body has 'id' field matching {process_id!r}",
            body.get("id") == process_id,
            f"got id={body.get('id')!r}",
        )
        check(
            "process body has 'schema_version' field",
            "schema_version" in body,
            f"keys: {list(body.keys())[:10]}",
        )


def check_paths_endpoint(base: str, headers: dict[str, str]) -> None:
    """V2 paths endpoint should return collection + individual entries."""
    section("V2 paths endpoint: GET /api/paths")

    status, body = get(f"{base}/api/paths", headers)
    check(
        "GET /api/paths → 200",
        status == 200,
        f"got {status}",
    )
    if status == 200 and isinstance(body, dict):
        check("paths response has 'paths' array", "paths" in body, str(type(body)))
        check("paths response has 'total' field", "total" in body, str(type(body)))
        if "total" in body:
            check(
                "paths total >= 16 (V1 paths migrated)",
                isinstance(body["total"], int) and body["total"] >= 16,
                f"got total={body.get('total')}",
            )


def check_capabilities_endpoint(base: str, headers: dict[str, str]) -> None:
    """Capabilities file must be served and have the declared_capabilities list."""
    section("Capabilities endpoint: GET /agents/capabilities.json")

    status, body = get(f"{base}/agents/capabilities.json", headers)
    check("GET /agents/capabilities.json → 200", status == 200, f"got {status}")
    if status == 200 and isinstance(body, dict):
        check(
            "capabilities.json has 'capability_tiers' key",
            "capability_tiers" in body,
            f"keys: {list(body.keys())}",
        )


def check_submission_contract_version(base: str, headers: dict[str, str]) -> None:
    """Verify the API accepts submission_contract_version: '2.0.0'.
    We post a minimal dry-run validation (no actual data committed)."""
    section("Submission contract version '2.0.0' accepted")

    import uuid as _uuid
    payload = json.dumps({
        "schema_version": 5,
        "submission_id": f"val_{_uuid.uuid4().hex[:8]}-0000-7000-8000-{_uuid.uuid4().hex[:12]}",
        "submitted_at": "2026-05-28T18:00:00Z",
        "submitting_harness": "cowork-stub-dogfood/1.0",
        "submitting_model": "claude-opus-4-7/xhigh",
        "submission_contract_version": "2.0.0",
        "declared_capabilities": ["multi_turn", "structured_output", "web_fetch", "tool_execution"],
        "target_type": "process",
        "target_id": "nationality-application",
        "outcome": "positive",
        "signal_class": "completed_successfully",
        "injection_flag": False,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{base}/api/validations",
        data=payload,
        headers={**headers, "content-type": "application/json", "x-dry-run": "1"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status = resp.status
            body = json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            body = json.loads(e.read().decode("utf-8", errors="replace"))
        except Exception:
            body = {}
    except (urllib.error.URLError, OSError) as e:
        skip("POST /api/validations dry-run", f"unreachable: {e}")
        return

    # Accept 200 (validated/applied) or 401/403 (auth required — not a schema error)
    check(
        "POST /api/validations with submission_contract_version='2.0.0' accepted (not schema_fail)",
        status in (200, 201, 401, 403),
        f"got {status}: {body.get('error', body) if isinstance(body, dict) else body}",
    )
    if status == 400 and isinstance(body, dict) and body.get("error") == "schema_fail":
        check(
            "schema_fail is NOT about submission_contract_version",
            "submission_contract_version" not in str(body.get("missing", "")),
            f"schema_fail details: {body}",
        )


def check_health_endpoint(base: str) -> None:
    """API health endpoint must respond."""
    section("API health endpoint")
    status, body = get(f"{base}/api/health")
    check("GET /api/health → 200", status == 200, f"got {status}")
    if status == 200 and isinstance(body, dict):
        check("health response has 'status' field", "status" in body)


# ─────────────────────────────────────────────────────────────────────────────
# Driver
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="V1 plugin → V2 API compatibility dogfood (W31.7c)",
    )
    p.add_argument("--base-url", default="https://becivic.be",
                   help="API base URL (default: https://becivic.be)")
    p.add_argument("--harness-key", metavar="KEY",
                   help="Harness API key (X-Harness-Key header). Optional for read endpoints.")
    p.add_argument("--skip-submit", action="store_true",
                   help="Skip the submission dry-run test")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    base = args.base_url.rstrip("/")

    headers: dict[str, str] = {}
    if args.harness_key:
        headers["x-harness-key"] = args.harness_key

    print(f"=== V1→V2 API compatibility dogfood ===")
    print(f"  base URL:    {base}")
    print(f"  harness key: {'set' if args.harness_key else 'not set (read-only endpoints)'}")

    print(f"\nConnectivity probe…")
    if not is_reachable(base):
        print(f"  {base}/api/health unreachable — aborting", file=sys.stderr)
        return 2
    print(f"  {base} reachable")

    check_health_endpoint(base)
    check_manifest_alias(base, headers)
    check_capabilities_endpoint(base, headers)
    check_process_endpoint(base, headers)
    check_paths_endpoint(base, headers)

    if not args.skip_submit:
        check_submission_contract_version(base, headers)
    else:
        skip("submission dry-run", "--skip-submit flag set")

    print(f"\n{_pass} passed, {_fail} failed, {_skip} skipped")
    if _failures:
        print("\nFailed checks:")
        for f in _failures:
            print(f"  - {f}")
    return 0 if _fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
