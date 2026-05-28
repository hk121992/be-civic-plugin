#!/usr/bin/env python3
"""cowork-stub.py — W31.7b

Cowork stub harness for Claude-Code-side dogfood.

Sets up the two-surface substrate layout under ~/.be-civic-stub/ and prints
the env-var assignments that activate it. Intended to be sourced or run as
part of a Claude Code session that replaces the real Cowork plugin runtime.

Stubs provided:
  - mcp__cowork__request_cowork_directory: asks the operator for a path via
    stdin, then creates the BeCivic/ directory at that location.
  - mcp__visualize__show_widget: renders an HTML template to a temp file and
    opens it in the default browser (xdg-open / open / start).

Explicit stub signalling:
  Every stub emits a STUB_ACTIVE marker so operator sessions can see what is
  and is not native Cowork behaviour. This is a firm design requirement from
  the sprint spec: "Cowork-specific surface differences are explicit".

Usage:
  python3 stubs/cowork-stub.py [--setup] [--show-env]
  eval "$(python3 stubs/cowork-stub.py --show-env)"

  # Or in a session CLAUDE.md session-start hook:
  python3 ${CLAUDE_PLUGIN_ROOT}/stubs/cowork-stub.py --setup

Spec: W31.7b, bc-workspace/roadmap/sprints/2026-W31-v2-api-and-auth.md §Phase7
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import uuid
import webbrowser
from datetime import datetime, timezone
from pathlib import Path


STUB_BASE = Path.home() / ".be-civic-stub"
STUB_VISIBLE = STUB_BASE / "BeCivic"          # SUBSTRATE_DATA (user-visible)
STUB_STATE = STUB_BASE / "plugin-data"        # SUBSTRATE_STATE (hidden)
PLUGIN_ROOT = Path(__file__).resolve().parent.parent  # be-civic-plugin root


# ─────────────────────────────────────────────────────────────────────────────
# Stub: mcp__cowork__request_cowork_directory
# ─────────────────────────────────────────────────────────────────────────────

def stub_request_cowork_directory(suggested_parent: str | None = None) -> Path:
    """Stub for mcp__cowork__request_cowork_directory.

    In real Cowork: opens the native directory-picker UI so the user can
    choose where their BeCivic/ folder lives.
    In stub mode: asks the operator for a path via stdin (or uses the default).
    """
    print("\n[STUB_ACTIVE: mcp__cowork__request_cowork_directory]")
    print("  Real Cowork would show a native directory-picker here.")
    print(f"  Default: {STUB_VISIBLE}")

    if sys.stdin.isatty():
        choice = input(f"  Enter parent directory path (or press Enter for default): ").strip()
        parent = Path(choice) if choice else STUB_VISIBLE.parent
    else:
        parent = STUB_VISIBLE.parent
        print(f"  Non-interactive mode: using default {parent}")

    becivic_dir = parent / "BeCivic"
    return becivic_dir


# ─────────────────────────────────────────────────────────────────────────────
# Stub: mcp__visualize__show_widget
# ─────────────────────────────────────────────────────────────────────────────

def stub_show_widget(html_content: str, title: str = "Be Civic Widget") -> str:
    """Stub for mcp__visualize__show_widget.

    In real Cowork: renders the HTML inside the Cowork panel as a live widget.
    In stub mode: writes the HTML to a temp file and opens it in the browser.

    Returns the path to the temp file.
    """
    print("\n[STUB_ACTIVE: mcp__visualize__show_widget]")
    print("  Real Cowork would render this inside the Cowork sidebar panel.")
    print(f"  Stub: writing HTML to temp file + opening in browser.")

    fd, path = tempfile.mkstemp(suffix=".html", prefix="be-civic-widget-")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f5f5f5; margin: 0; padding: 1.5rem; }}
    .stub-banner {{
      background: #fff3cd; border: 1px solid #ffc107; border-radius: 6px;
      padding: 0.75rem 1rem; margin-bottom: 1.5rem; font-size: 0.85rem;
      color: #856404;
    }}
    .widget-container {{ background: white; border-radius: 8px;
                          box-shadow: 0 1px 4px rgba(0,0,0,.12); padding: 1.5rem; }}
  </style>
</head>
<body>
  <div class="stub-banner">
    <strong>STUB_ACTIVE:</strong> mcp__visualize__show_widget — real Cowork renders this
    inline; stub mode renders to browser tab.
  </div>
  <div class="widget-container">
    {html_content}
  </div>
</body>
</html>""")

    webbrowser.open(f"file://{path}")
    print(f"  Opened: file://{path}")
    return path


# ─────────────────────────────────────────────────────────────────────────────
# Substrate scaffold — create the two-surface layout
# ─────────────────────────────────────────────────────────────────────────────

def setup_substrate(visible: Path, state: Path) -> None:
    """Create the two-surface substrate layout with required skeleton files.

    Per 40-substrate §4.1:
      Hidden (SUBSTRATE_STATE): .env, profile.json, preferences.json,
        events.jsonl, relationships.json, procedures.json,
        version.json, user-id
      Visible (SUBSTRATE_DATA): MEMORY.md, .be-civic/marker, CLAUDE.md
    """
    print(f"\nSetting up stub substrate:")
    print(f"  SUBSTRATE_DATA  = {visible}")
    print(f"  SUBSTRATE_STATE = {state}")

    visible.mkdir(parents=True, exist_ok=True)
    state.mkdir(parents=True, exist_ok=True)

    now = datetime.now(tz=timezone.utc).isoformat()

    # ── Hidden surface skeleton ─────────────────────────────────────────────

    # user-id (§2)
    uid_path = state / "user-id"
    if not uid_path.exists():
        uid_path.write_text(str(uuid.uuid4()), encoding="utf-8")
        print(f"  created {uid_path.relative_to(Path.home())}")

    # profile.json (§4)
    profile_path = state / "profile.json"
    if not profile_path.exists():
        profile_path.write_text(json.dumps({
            "schema_version": 1,
            "display_name": "",
            "region": "",
            "commune_nis5": "",
            "residency_status": "",
            "civic_status": "",
            "created_at": now,
            "updated_at": now,
        }, indent=2) + "\n", encoding="utf-8")
        print(f"  created {profile_path.relative_to(Path.home())}")

    # preferences.json (§5)
    prefs_path = state / "preferences.json"
    if not prefs_path.exists():
        prefs_path.write_text(json.dumps({
            "schema_version": 1,
            "telemetry_opt_in": False,
            "conversation_language": "en",
            "created_at": now,
        }, indent=2) + "\n", encoding="utf-8")
        print(f"  created {prefs_path.relative_to(Path.home())}")

    # events.jsonl (§6) — empty to start
    events_path = state / "events.jsonl"
    if not events_path.exists():
        events_path.write_text("", encoding="utf-8")
        print(f"  created {events_path.relative_to(Path.home())}")

    # relationships.json (§7)
    rel_path = state / "relationships.json"
    if not rel_path.exists():
        rel_path.write_text(json.dumps({
            "schema_version": 1,
            "relationships": [],
        }, indent=2) + "\n", encoding="utf-8")
        print(f"  created {rel_path.relative_to(Path.home())}")

    # procedures.json (§8)
    proc_path = state / "procedures.json"
    if not proc_path.exists():
        proc_path.write_text(json.dumps({
            "schema_version": 1,
            "procedures": {},
        }, indent=2) + "\n", encoding="utf-8")
        print(f"  created {proc_path.relative_to(Path.home())}")

    # version.json (§7.1)
    version_path = state / "version.json"
    if not version_path.exists():
        version_path.write_text(json.dumps({
            "plugin_version": "0.2.1",
            "state_version": "0.2.1",
        }, indent=2) + "\n", encoding="utf-8")
        print(f"  created {version_path.relative_to(Path.home())}")

    # .env Identity slot (§6.1) — empty placeholder; never populated by this script
    env_path = state / ".env"
    if not env_path.exists():
        env_path.write_text(
            "# Identity slot — per 40-substrate §6.1.\n"
            "# Never committed to git. Never echoed to chat.\n"
            "# Populated by the dossier-builder and bc-document-handler Tools.\n",
            encoding="utf-8",
        )
        print(f"  created {env_path.relative_to(Path.home())} (empty Identity slot)")

    # ── .gitignore for hidden surface — excludes Identity ──────────────────
    # Must be written BEFORE git init so the initial commit never tracks .env.
    hidden_gitignore = state / ".gitignore"
    if not hidden_gitignore.exists():
        hidden_gitignore.write_text(
            "# Per 40-substrate §6.1 — Identity never committed.\n"
            ".env\n",
            encoding="utf-8",
        )
        print(f"  created {hidden_gitignore.relative_to(Path.home())}")

    # ── Git init for hidden surface ─────────────────────────────────────────
    # .gitignore is written above before git init so .env is excluded from
    # the initial commit (40-substrate §6.1: Identity never committed).
    if not (state / ".git").exists():
        subprocess.run(["git", "init", "-q", str(state)], check=False)
        subprocess.run(
            ["git", "-C", str(state), "add", "--all"],
            check=False, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(state), "commit", "-q", "-m", "chore: init substrate state"],
            env={**os.environ, "GIT_AUTHOR_NAME": "Be Civic", "GIT_AUTHOR_EMAIL": "noreply@becivic.be",
                 "GIT_COMMITTER_NAME": "Be Civic", "GIT_COMMITTER_EMAIL": "noreply@becivic.be"},
            check=False, capture_output=True,
        )
        print(f"  git init {state.relative_to(Path.home())}")

    # ── Visible surface skeleton ────────────────────────────────────────────

    # MEMORY.md (§5)
    memory_path = visible / "MEMORY.md"
    if not memory_path.exists():
        memory_path.write_text(
            "# Be Civic — Memory\n\nStub substrate. No user notes yet.\n",
            encoding="utf-8",
        )
        print(f"  created {memory_path.relative_to(Path.home())}")

    # .be-civic/marker (§9.3)
    marker_dir = visible / ".be-civic"
    marker_dir.mkdir(exist_ok=True)
    marker_path = marker_dir / "marker"
    if not marker_path.exists():
        marker_path.write_text(
            json.dumps({
                "created_at": now,
                "procedures_registry": str(proc_path),
                "stub": True,
            }, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"  created {marker_path.relative_to(Path.home())}")

    # .gitignore for visible surface — per 51-cowork §7.3
    vis_gitignore = visible / ".gitignore"
    if not vis_gitignore.exists():
        vis_gitignore.write_text(
            "# Per 51-cowork §7.3 + 40-substrate §6.1\n"
            "# documents/ not tracked (GDPR Right to Erasure)\n"
            "documents/\n"
            "# tmp files\n"
            "*.tmp\n",
            encoding="utf-8",
        )
        print(f"  created {vis_gitignore.relative_to(Path.home())}")

    # CLAUDE.md template (51-cowork §6 — harness auto-load)
    claude_md = visible / "CLAUDE.md"
    if not claude_md.exists():
        claude_md.write_text(
            "---\n"
            "# Be Civic — Cowork stub harness\n"
            "# Auto-loaded by Cowork ancestor-walk (51-cowork §6).\n"
            "# In real Cowork this file is provisioned from ${SUBSTRATE_ROOT}/data/CLAUDE.md.\n"
            "---\n\n"
            "This is the Be Civic Cowork stub harness. See be-civic-plugin/stubs/cowork-stub.py.\n",
            encoding="utf-8",
        )
        print(f"  created {claude_md.relative_to(Path.home())}")

    # ── Git init for visible surface ────────────────────────────────────────
    if not (visible / ".git").exists():
        subprocess.run(["git", "init", "-q", str(visible)], check=False)
        subprocess.run(
            ["git", "-C", str(visible), "add", "--all"],
            check=False, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(visible), "commit", "-q", "-m", "chore: init substrate visible surface"],
            env={**os.environ, "GIT_AUTHOR_NAME": "Be Civic", "GIT_AUTHOR_EMAIL": "noreply@becivic.be",
                 "GIT_COMMITTER_NAME": "Be Civic", "GIT_COMMITTER_EMAIL": "noreply@becivic.be"},
            check=False, capture_output=True,
        )
        print(f"  git init {visible.relative_to(Path.home())}")

    print("\n✓ Stub substrate ready.")


def show_env(visible: Path, state: Path, root: Path) -> None:
    """Print shell env-var assignments for the stub harness."""
    print(f"export CLAUDE_PLUGIN_DATA={state}")
    print(f"export CLAUDE_PLUGIN_DATA_VISIBLE={visible}")
    print(f"export CLAUDE_PLUGIN_ROOT={root}")


# ─────────────────────────────────────────────────────────────────────────────
# Driver
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser(
        description="Cowork stub harness setup for Claude-Code-side dogfood (W31.7b)",
    )
    p.add_argument("--setup", action="store_true",
                   help="Create/update the two-surface substrate layout")
    p.add_argument("--show-env", action="store_true",
                   help="Print shell env exports (suitable for eval)")
    p.add_argument("--visible", metavar="PATH", default=str(STUB_VISIBLE),
                   help=f"${'{SUBSTRATE_DATA}'} override (default: {STUB_VISIBLE})")
    p.add_argument("--state", metavar="PATH", default=str(STUB_STATE),
                   help=f"${'{SUBSTRATE_STATE}'} override (default: {STUB_STATE})")
    args = p.parse_args()

    visible = Path(args.visible)
    state = Path(args.state)

    if args.setup:
        setup_substrate(visible, state)

    if args.show_env:
        show_env(visible, state, PLUGIN_ROOT)

    if not args.setup and not args.show_env:
        p.print_help()
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
