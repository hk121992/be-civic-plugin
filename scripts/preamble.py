#!/usr/bin/env python3
"""preamble.py — orchestrator.

Runs every preamble check in dependency order; emits one combined stream of
`KEY: VALUE` lines on stdout for CLAUDE.md to parse into session state.

Order (per design doc, simplified 2026-05-15 — tier system dropped):
  1. Verify writable bundle root (fail fast if read-only — install error)
  2. Generate SESSION_ID and resolve USER_DATA_DIR
  3. scan-orphan-buffers.py
  4. scan-pending-state.py
  5. detect-browser-capability.py
  6. Emit profile.json contents inline (so the harness skips a Read tool call)

The harness runs in Cowork plugin context where filesystem availability is a
given (bundle root is the writable project folder). Tier-conditional logic
(T0/T1/T2/T3) was removed 2026-05-15 — the harness now assumes filesystem
availability and fails fast if it's wrong.

Network fetches (skills-graph, path-directory, scrub-rules) are NOT in the
preamble. CLAUDE.md guidance instructs the agent to fetch them inline at
first-use via the MCP → HTTPS → WebFetch fallback chain (see §6).

Total time budget: <500ms (all local; no network).
Failure semantics: hard-fail on read-only bundle root. On any sub-script
error, emit a `<NAME>: probe_failed` marker and continue. If the orchestrator
itself fails before completing, emit JIT_FALLBACK so CLAUDE.md discovers
capabilities just-in-time from its own tool list.

Runtime: Python 3 stdlib only. No third-party dependencies.
Cross-platform: macOS, Windows (native, not WSL), Linux.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
import uuid
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parent
# Plugin-aware paths: CLAUDE_PLUGIN_ROOT is the read-only plugin install
# directory; CLAUDE_PLUGIN_DATA is the writable state directory that survives
# plugin updates. Fall back to the script's parent (Cowork-Project model) when
# the env vars are absent.
PLUGIN_ROOT = Path(os.environ.get("CLAUDE_PLUGIN_ROOT", str(SCRIPTS_DIR.parent)))
USER_DATA_DIR = Path(os.environ.get("CLAUDE_PLUGIN_DATA", str(PLUGIN_ROOT)))
BUNDLE_ROOT = PLUGIN_ROOT  # back-compat alias; read-only files live here


JIT_FALLBACK = """\
PREAMBLE: fallback_active
PREAMBLE_JIT_GUIDANCE: |
  The preamble couldn't complete — orchestrator failed before producing full
  state. Proceed with safe defaults AND discover capabilities just-in-time:

  - SESSION_ID: generate a UUIDv7 yourself for this session.
  - USER_DATA_DIR: assume the bundle root folder.
  - PENDING_STATE: assume none. If you find unsubmitted observation files
    or research-notes files older than this session start, treat as pending.
  - BECIVIC_MCP_CONNECTED: check your own tool list for `mcp__becivic__*`.
  - CHROME_MCP_CONNECTED: same — check for `mcp__claude_in_chrome__*`.
  - CHROME_INSTALLED: ask the customer once at first browser-needing step
    rather than running a pre-emptive setup walkthrough.

  In short: behave as if all flags are unknown but DO actively check when a
  flag matters.
"""

WRITE_FAILURE = """\
PREAMBLE: fatal
PREAMBLE_ERROR: bundle_root_read_only
PREAMBLE_DETAIL: |
  The bundle root is not writable. Be Civic needs a writable project folder
  to save customer state, observation buffers, and research notes.

  If you installed this as a Cowork plugin pointing at a folder you own, this
  is an install error — check folder permissions. If you opened the bundle
  from a read-only location (a zip, a system folder, a network share without
  write access), copy it to a writable location and reopen.

  The harness cannot proceed.
"""


def verify_writable() -> bool:
    """Quick write test against the user data dir. True if writable."""
    try:
        USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False
    probe = USER_DATA_DIR / f".preamble-probe-{uuid.uuid4().hex[:8]}"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def new_session_id() -> str:
    """UUIDv7-ish identifier (stdlib lacks uuid7; combine time+random)."""
    ts = int(time.time() * 1000)
    rnd = uuid.uuid4().hex[:16]
    return f"ses_{ts:013x}-{rnd}"


def run_script(name: str) -> tuple[bool, str]:
    """Run a sibling script and capture its stdout."""
    script_path = SCRIPTS_DIR / name
    if not script_path.exists():
        return False, f"{name.upper().replace('-', '_').replace('.PY', '')}: missing"
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False, ""
    ok = result.returncode == 0
    return ok, result.stdout.rstrip()


def emit_profile_json() -> None:
    """Emit profile.json contents inline so the harness doesn't have to Read it.

    Read from USER_DATA_DIR first (customer state). Fall back to PLUGIN_ROOT
    (template shipped with the plugin) on first-contact when no customer state
    exists yet.
    """
    candidates = [
        USER_DATA_DIR / "profile.json",
        PLUGIN_ROOT / "profile.json",
    ]
    for profile_path in candidates:
        if profile_path.exists():
            try:
                content = profile_path.read_text(encoding="utf-8")
            except OSError:
                continue
            print(f"PROFILE_JSON_SOURCE: {profile_path}")
            print("PROFILE_JSON: inline_below")
            print("PROFILE_JSON_BEGIN")
            print(content.rstrip())
            print("PROFILE_JSON_END")
            return
    print("PROFILE_JSON: absent")


def main() -> int:
    # 1. Writable-bundle hard check. Fail fast if not.
    if not verify_writable():
        print(WRITE_FAILURE)
        return 1

    # 2. Session id + USER_DATA_DIR.
    session_id = new_session_id()
    user_data_dir = os.environ.get("BC_USER_DATA_DIR", str(USER_DATA_DIR))
    print(f"SESSION_ID: {session_id}")
    print(f"USER_DATA_DIR: {user_data_dir}")
    print(f"PLUGIN_ROOT: {PLUGIN_ROOT}")
    print(f"SESSION_STATE_DIR: {user_data_dir}/sessions/{session_id}/state/")

    # 3. Orphan-buffers scan.
    ok, orphan_output = run_script("scan-orphan-buffers.py")
    if ok and orphan_output:
        print(orphan_output)
    elif not ok:
        print("ORPHAN_SESSIONS_CLEANED: probe_failed")

    # 4. Pending-state scan.
    ok, pending_output = run_script("scan-pending-state.py")
    if ok and pending_output:
        print(pending_output)
    elif not ok:
        print("PENDING_STATE: probe_failed")

    # 5. Browser capability.
    ok, browser_output = run_script("detect-browser-capability.py")
    if ok and browser_output:
        print(browser_output)
    elif not ok:
        print("CHROME_INSTALLED: unknown")
        print("OS_PLATFORM: unknown")

    # 6. Profile inline.
    emit_profile_json()

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Catch-all: if orchestration itself crashes, emit fallback so the
        # harness never sees a half-written preamble.
        print(JIT_FALLBACK)
        try:
            emit_profile_json()
        except Exception:
            print("PROFILE_JSON: probe_failed")
        sys.exit(1)
