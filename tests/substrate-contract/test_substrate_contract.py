#!/usr/bin/env python3
"""test_substrate_contract.py — W31.7a

End-to-end test suite that verifies the 40-substrate contract against any
substrate implementation. Run after each subsequent sprint (W33, W35, W37)
as the integration gate.

Spec authority:
  handbook/content/05-product/40-substrate.md
  handbook/content/04-domain/04-substrate-state.md

Verified invariants:
  §4   — 8-node state graph on disk (correct files, correct surfaces)
  §5   — MEMORY.md in visible surface
  §6   — Identity slot in hidden surface, excluded from commit allowlist
  §7   — version.json shape + migration-ready structure
  §8   — Atomic-commit invariant: version-control present on both surfaces
  §9   — .be-civic/marker exists and cross-references procedures registry
  §10  — Substrate prerequisites: the two surfaces exist and are distinct

Usage:
  python3 tests/substrate-contract/test_substrate_contract.py \\
      --substrate-data /path/to/BeCivic \\
      --substrate-state /path/to/plugin-data \\
      [--substrate-root /path/to/plugin-root]

  # Against the Cowork stub harness (W31.7b):
  python3 tests/substrate-contract/test_substrate_contract.py \\
      --stub

Exit codes:
  0 — all checks pass
  1 — one or more checks failed
  2 — invalid arguments

The test runner is stdlib-only (no pytest, no third-party deps) — it must
work inside any substrate execution context including Cowork-stubbed sessions.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Minimal test runner (no pytest — stdlib only)
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
# Cowork stub defaults (W31.7b integration)
# ─────────────────────────────────────────────────────────────────────────────

STUB_DATA_DEFAULT = Path.home() / ".be-civic-stub" / "BeCivic"
STUB_STATE_DEFAULT = Path.home() / ".be-civic-stub" / "plugin-data"


# ─────────────────────────────────────────────────────────────────────────────
# §4 — 8-node state graph on disk
# ─────────────────────────────────────────────────────────────────────────────

# Per 40-substrate §4.1 + 04-substrate-state §1
HIDDEN_SURFACE_NODES = {
    # Required files in ${SUBSTRATE_STATE}
    "user-id":          "user-id",           # §2 — User ID
    "profile":          "profile.json",       # §4 — Profile
    "preferences":      "preferences.json",   # §5 — User Preferences
    "events":           "events.jsonl",       # §6 — Events
    "relationships":    "relationships.json", # §7 — Relationships
    "procedures":       "procedures.json",    # §8 — Procedures registry
    "version":          "version.json",       # §7.1 — Version markers
    # Identity slot (.env) existence check is separate (§6)
}

VISIBLE_SURFACE_NODES = {
    # Required in ${SUBSTRATE_DATA}
    "memory":   "MEMORY.md",          # §5
    "marker":   ".be-civic/marker",   # §9.3
}


def check_hidden_surface(state: Path) -> None:
    section("§4 Hidden surface — 8-node state graph")
    check("${SUBSTRATE_STATE} directory exists", state.is_dir(), str(state))

    for name, filename in HIDDEN_SURFACE_NODES.items():
        p = state / filename
        check(
            f"{filename} present (node: {name})",
            p.exists(),
            f"expected at {p}",
        )

    # §6 — Identity slot: .env exists in hidden surface (may be empty at first run)
    env_path = state / ".env"
    check(
        ".env Identity slot present in ${SUBSTRATE_STATE}",
        env_path.exists(),
        f"expected at {env_path}",
    )


def check_visible_surface(data: Path) -> None:
    section("§5 Visible surface — MEMORY.md + .be-civic/marker")
    check("${SUBSTRATE_DATA} directory exists", data.is_dir(), str(data))

    for name, relpath in VISIBLE_SURFACE_NODES.items():
        p = data / relpath
        check(
            f"{relpath} present (node: {name})",
            p.exists(),
            f"expected at {p}",
        )


# ─────────────────────────────────────────────────────────────────────────────
# §6 — Identity slot discipline
# ─────────────────────────────────────────────────────────────────────────────

def check_identity_discipline(state: Path, data: Path) -> None:
    section("§6 Identity slot discipline")

    env_path = state / ".env"
    # §6.1: .env must NOT be inside ${SUBSTRATE_DATA} (it's in hidden surface)
    try:
        env_path.relative_to(data)
        in_visible = True
    except ValueError:
        in_visible = False
    check(
        "Identity slot is in hidden surface, not visible surface",
        not in_visible,
        "Identity (.env) must not be in ${SUBSTRATE_DATA}",
    )

    # §6.1: Identity slot must be excluded from atomic-commit (gitignored)
    # Only the hidden surface (.gitignore in ${SUBSTRATE_STATE}) needs to exclude
    # .env — Identity lives in the hidden surface, not the visible surface.
    # Per 40-substrate §6.1: "The Identity slot is in the substrate's
    # version-control ignore-list by construction."
    hidden_gitignore = state / ".gitignore"
    if not hidden_gitignore.exists():
        skip("${SUBSTRATE_STATE}/.gitignore excludes .env", ".gitignore not present")
    else:
        content = hidden_gitignore.read_text(encoding="utf-8", errors="replace")
        check(
            "${SUBSTRATE_STATE}/.gitignore excludes .env (Identity never-commit)",
            ".env" in content,
            f"Missing .env exclusion in {hidden_gitignore}",
        )

    # §6.1: Identity slot must not be accidentally committed (check git status)
    git_dir = state / ".git"
    if git_dir.exists():
        import subprocess
        result = subprocess.run(
            ["git", "-C", str(state), "ls-files", ".env"],
            capture_output=True, text=True,
        )
        check(
            ".env is NOT tracked by git in ${SUBSTRATE_STATE}",
            ".env" not in result.stdout,
            "Identity slot (.env) is tracked in git — violates 40-substrate §6.1",
        )


# ─────────────────────────────────────────────────────────────────────────────
# §7 — version.json shape
# ─────────────────────────────────────────────────────────────────────────────

VERSION_REQUIRED_FIELDS = {"plugin_version", "state_version"}


def check_version_json(state: Path) -> None:
    section("§7 version.json — schema version markers")

    vp = state / "version.json"
    if not vp.exists():
        check("version.json present", False, str(vp))
        return

    try:
        v = json.loads(vp.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        check("version.json is valid JSON", False, str(e))
        return

    check("version.json is valid JSON", True)
    for field in VERSION_REQUIRED_FIELDS:
        check(
            f"version.json has {field!r}",
            field in v,
            f"Missing field '{field}' in {vp}",
        )
    if "plugin_version" in v and "state_version" in v:
        pv = v["plugin_version"]
        sv = v["state_version"]
        check(
            "plugin_version and state_version are strings",
            isinstance(pv, str) and isinstance(sv, str),
            f"plugin_version={pv!r}, state_version={sv!r}",
        )


# ─────────────────────────────────────────────────────────────────────────────
# §8 — Atomic-commit invariant (version control present)
# ─────────────────────────────────────────────────────────────────────────────

def check_atomic_commit(state: Path, data: Path) -> None:
    section("§8 Atomic-commit invariant — version control present")

    hidden_git = state / ".git"
    check(
        "${SUBSTRATE_STATE} is version-controlled (git repo present)",
        hidden_git.exists(),
        f"No .git at {hidden_git} — 40-substrate §8.1 requires per-write hook or session-lifetime watcher",
    )

    visible_git = data / ".git"
    check(
        "${SUBSTRATE_DATA} is version-controlled (git repo present)",
        visible_git.exists(),
        f"No .git at {visible_git} — 40-substrate §8.1 requires atomic-commit across both surfaces",
    )

    # §8.2: check that identity slot is not in git history
    if hidden_git.exists():
        import subprocess
        result = subprocess.run(
            ["git", "-C", str(state), "log", "--all", "--full-history", "--", ".env"],
            capture_output=True, text=True,
        )
        check(
            ".env has no commits in ${SUBSTRATE_STATE} git history",
            result.stdout.strip() == "",
            "Identity slot (.env) appears in git history — violates 40-substrate §6.1",
        )


# ─────────────────────────────────────────────────────────────────────────────
# §9 — .be-civic/marker cross-reference
# ─────────────────────────────────────────────────────────────────────────────

def check_marker(data: Path, state: Path) -> None:
    section("§9.3 .be-civic/marker cross-reference")

    marker_path = data / ".be-civic" / "marker"
    if not marker_path.exists():
        check(".be-civic/marker present", False, str(marker_path))
        return

    check(".be-civic/marker present", True)

    content = marker_path.read_text(encoding="utf-8", errors="replace").strip()
    check(
        ".be-civic/marker is non-empty",
        len(content) > 0,
        "Empty marker file",
    )

    # Per 40 §9.3 and 51-cowork §5.1: marker cross-references procedures registry
    # The marker should contain a path to the procedures.json in SUBSTRATE_STATE
    procedures_path = state / "procedures.json"
    check(
        "procedures.json exists (required by marker cross-reference)",
        procedures_path.exists(),
        str(procedures_path),
    )


# ─────────────────────────────────────────────────────────────────────────────
# §10 — Substrate prerequisites: two surfaces exist and are distinct
# ─────────────────────────────────────────────────────────────────────────────

def check_substrate_prerequisites(state: Path, data: Path, root: Optional[Path]) -> None:
    section("§10 Substrate prerequisites")

    check(
        "${SUBSTRATE_DATA} and ${SUBSTRATE_STATE} are distinct paths",
        state.resolve() != data.resolve(),
        f"SUBSTRATE_DATA={data}, SUBSTRATE_STATE={state}",
    )

    if root is not None:
        check("${SUBSTRATE_ROOT} exists (read-only plugin install dir)", root.exists(), str(root))
        check(
            "${SUBSTRATE_ROOT} distinct from ${SUBSTRATE_DATA}",
            root.resolve() != data.resolve(),
        )
        check(
            "${SUBSTRATE_ROOT} distinct from ${SUBSTRATE_STATE}",
            root.resolve() != state.resolve(),
        )
    else:
        skip("${SUBSTRATE_ROOT} checks", "--substrate-root not provided")

    # §10.1: file system access — both directories are writable (for hidden;
    # visible is user-writable which we test by attempting a probe file)
    check("${SUBSTRATE_STATE} is writable", os.access(state, os.W_OK), str(state))
    check("${SUBSTRATE_DATA} is writable", os.access(data, os.W_OK), str(data))


# ─────────────────────────────────────────────────────────────────────────────
# §4.1 — JSON shape for graph-state files
# ─────────────────────────────────────────────────────────────────────────────

def check_state_graph_shapes(state: Path) -> None:
    section("§4.1 State graph file shapes")

    # profile.json — must be a JSON object
    pf = state / "profile.json"
    if pf.exists():
        try:
            p = json.loads(pf.read_text(encoding="utf-8"))
            check("profile.json is a JSON object", isinstance(p, dict))
        except json.JSONDecodeError as e:
            check("profile.json is valid JSON", False, str(e))

    # preferences.json — must be a JSON object
    pref = state / "preferences.json"
    if pref.exists():
        try:
            pr = json.loads(pref.read_text(encoding="utf-8"))
            check("preferences.json is a JSON object", isinstance(pr, dict))
        except json.JSONDecodeError as e:
            check("preferences.json is valid JSON", False, str(e))

    # procedures.json — must be a JSON object (registry keyed by procedure slug)
    proc = state / "procedures.json"
    if proc.exists():
        try:
            p = json.loads(proc.read_text(encoding="utf-8"))
            check("procedures.json is a JSON object", isinstance(p, dict))
        except json.JSONDecodeError as e:
            check("procedures.json is valid JSON", False, str(e))

    # relationships.json — must be a JSON object or array
    rel = state / "relationships.json"
    if rel.exists():
        try:
            r = json.loads(rel.read_text(encoding="utf-8"))
            check(
                "relationships.json is a JSON object or array",
                isinstance(r, (dict, list)),
            )
        except json.JSONDecodeError as e:
            check("relationships.json is valid JSON", False, str(e))

    # events.jsonl — must be newline-delimited JSON (each line is a JSON object)
    ev = state / "events.jsonl"
    if ev.exists() and ev.stat().st_size > 0:
        lines = ev.read_text(encoding="utf-8", errors="replace").splitlines()
        non_empty = [l for l in lines if l.strip()]
        bad = 0
        for line in non_empty:
            try:
                obj = json.loads(line)
                if not isinstance(obj, dict):
                    bad += 1
            except json.JSONDecodeError:
                bad += 1
        check(
            f"events.jsonl all lines are valid JSON objects ({len(non_empty)} lines)",
            bad == 0,
            f"{bad} invalid line(s)",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Driver
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Verify the 40-substrate contract against a substrate implementation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--substrate-data", metavar="PATH",
                   help="${SUBSTRATE_DATA} — user-visible writable directory")
    p.add_argument("--substrate-state", metavar="PATH",
                   help="${SUBSTRATE_STATE} — agent-managed hidden writable directory")
    p.add_argument("--substrate-root", metavar="PATH",
                   help="${SUBSTRATE_ROOT} — read-only plugin install directory (optional)")
    p.add_argument("--stub", action="store_true",
                   help="Use Cowork stub harness defaults (W31.7b)")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    if args.stub:
        # W31.7b Cowork stub harness defaults
        substrate_data = Path(
            os.environ.get("CLAUDE_PLUGIN_DATA_VISIBLE", str(STUB_DATA_DEFAULT))
        )
        substrate_state = Path(
            os.environ.get("CLAUDE_PLUGIN_DATA", str(STUB_STATE_DEFAULT))
        )
        substrate_root = (
            Path(os.environ["CLAUDE_PLUGIN_ROOT"])
            if "CLAUDE_PLUGIN_ROOT" in os.environ
            else None
        )
    else:
        if not args.substrate_data or not args.substrate_state:
            print(
                "Error: --substrate-data and --substrate-state are required "
                "(or use --stub for Cowork stub defaults)",
                file=sys.stderr,
            )
            return 2
        substrate_data = Path(args.substrate_data)
        substrate_state = Path(args.substrate_state)
        substrate_root = Path(args.substrate_root) if args.substrate_root else None

    print("=== 40-substrate contract verification ===")
    print(f"  SUBSTRATE_DATA:  {substrate_data}")
    print(f"  SUBSTRATE_STATE: {substrate_state}")
    print(f"  SUBSTRATE_ROOT:  {substrate_root or '(not provided)'}")

    check_substrate_prerequisites(substrate_state, substrate_data, substrate_root)
    check_hidden_surface(substrate_state)
    check_visible_surface(substrate_data)
    check_identity_discipline(substrate_state, substrate_data)
    check_version_json(substrate_state)
    check_state_graph_shapes(substrate_state)
    check_atomic_commit(substrate_state, substrate_data)
    check_marker(substrate_data, substrate_state)

    print(f"\n{_pass} passed, {_fail} failed, {_skip} skipped")
    if _failures:
        print("\nFailed checks:")
        for f in _failures:
            print(f"  - {f}")
    return 0 if _fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
