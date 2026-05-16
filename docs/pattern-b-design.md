# Pattern B — CLAUDE.md as harness

**Status:** approved 2026-05-16
**Authored:** following the 2026-05-16 plugin-test retrospective at `bc-operations/docs/agent-ux/sessions/2026-05-16-plugin-test/`
**Companion docs:** plan-pattern-b-implementation (see `~/.claude/plans/`)

## The problem this solves

The first working session of the Be Civic Cowork plugin (16 May 2026) revealed a structural failure mode: the harness was driving the conversation cleanly during onboarding and procedure identification, then degraded into "agent-as-context" through the document-fetching middle. Two concrete symptoms:

1. **The agent stopped re-invoking peer skills.** After the first `path-traversal` invocation, it switched to direct `get_path(...)` calls and walked the source manually. That bypassed path-traversal §4.6, which is the capability gate that's *supposed* to fire Chrome MCP proactively. The user had to push the agent to open the browser — the structural rule for opening it was sitting inside a skill that was never re-invoked.
2. **Session-close never ran.** No drafter sub-agents spawned, no submissions to Be Civic happened, the observations buffer accumulated five entries that stayed as raw JSONL claims instead of becoming drafted amendments.

Both symptoms share one root cause: **a skill loaded once becomes "context the agent has already seen," and the agent's attention drifts back toward general-LLM behaviour over the course of a long session.** The harness rules — Iron Law, situation-assessment-before-verdict, observation-every-turn, path-traversal-on-Path-tag, auto-close-on-terminal-step — are load-bearing across the entire session, but they were only ever loaded once, into a skill body, that the agent eventually treated as background.

## The Pattern B shift

**The harness moves out of the be-civic skill body and into a CLAUDE.md sitting inside a Cowork Project folder owned by the customer.**

CLAUDE.md is loaded as session context on every conversation start in that folder, and contributes to the model's working context every turn. There is no decay equivalent to "skill became background" — the harness rules are part of system context for the lifetime of the session.

The plugin still ships, and ships almost everything it ships today. What changes is:

- The **be-civic skill** becomes a thin gate. It checks whether the conversation is running inside a Be Civic project (CLAUDE.md present). If not, it offers to set one up. If yes, it does nothing — the CLAUDE.md harness is already driving.
- The **peer skills** (`onboarding`, `discovery`, `document-handler`, `path-traversal`, `session-close`, `dossier-compilation`) remain in the plugin and are invoked by the harness when their mode applies. They become helpers driven by an always-on harness, instead of being the harness's only persistence surface.
- The **drafter sub-agents** (`be-civic-path-drafter`, `be-civic-skill-drafter`) remain in the plugin. Session-close spawns them automatically when the harness reaches a terminal step or the customer explicitly closes.
- **MCP wiring**, **state schemas**, and **Layer-1 scrub rules** all stay in the plugin unchanged.

## What ships where

| Artefact | Lives in plugin | Lives in user's project folder |
|---|---|---|
| Manifest (`plugin.json`, `marketplace.json`) | ✓ | — |
| `be-civic` skill (the thin gate) | ✓ | — |
| Peer skills (onboarding/discovery/etc.) | ✓ | — |
| Drafter sub-agents | ✓ | — |
| `.mcp.json` (MCP wiring) | ✓ | — |
| Schemas (`profile`, `observation.v3`) | ✓ | — |
| `data/scrub-rules.json` (fallback) | ✓ | — |
| Helper scripts (`preamble.py`, etc.) | ✓ | — |
| **Harness CLAUDE.md** | — | ✓ (written by onboarding) |
| `profile.json` (customer state) | — | ✓ |
| `memory.md` (narrative state) | — | ✓ |
| `documents/<procedure-id>/<doc>.<ext>` (archived originals) | — | ✓ |
| `sessions/<session-id>/observations-buffer.jsonl` | — | ✓ |
| `memory/research-notes-*.md` (discovery output) | — | ✓ |

The plugin is **stateless from the customer's perspective**. Every byte of customer state lives in their project folder, which they own, can back up, can share with their lawyer if they want, and can delete in one operation when they're done.

## Conversation lifecycle

### First conversation (no project yet)

1. User installs the be-civic plugin from the Cowork marketplace.
2. User starts a new conversation. They invoke `/be-civic` (or any peer skill, or the description-trigger fires from their first message).
3. The be-civic skill's gate runs. It checks the current directory for a CLAUDE.md identifying the folder as a Be Civic project.
4. **No project found.** Skill explains in plain language what a Be Civic project is and asks if the user wants to set one up. If yes:
   - Calls `mcp__cowork__request_cowork_directory` to let the user pick a folder.
   - Writes the harness CLAUDE.md into that folder.
   - Initialises empty `profile.json`, `memory.md`, `documents/`, `sessions/`, `memory/` per the state schema.
   - Hands control to the `onboarding` peer skill, which runs the full first-contact framing + intake form + initial procedure identification.
5. At the end of onboarding, the skill tells the user: **"From now on, open this folder in Cowork to continue. Start a new conversation pointed at it — the harness will be live from turn 1."**

### Subsequent conversations

1. User opens their Be Civic project folder in Cowork.
2. Cowork loads CLAUDE.md as system context.
3. The harness is live from turn 1. The first user message gets handled under harness discipline — pending-state check, branching on session type (returning / continuing / multi_active), procedure routing, situation assessment, etc.
4. No be-civic skill invocation needed. Peer skills are invoked by the harness when their mode applies, by name (`Skill: onboarding`, `Skill: path-traversal`, etc.). The harness's instructions on when to invoke each are part of the always-on context.

### Edge case: user invokes a Be Civic skill in a non-project conversation (e.g. they're working on something else and have a quick question)

1. The skill's gate checks for project context (CLAUDE.md present in the working directory or one of its parents).
2. **No project found.** Skill explains: "Be Civic works best inside a Be Civic project folder so I can keep your notes across sessions. Want to set one up? Or just want a one-off answer for this conversation?"
3. If one-off: skill answers in **advice-only mode** — no state persisted, no submissions to Be Civic, observations not buffered. The harness rules don't apply; this is a plain Q&A.
4. If set up project: standard onboarding flow.

### Edge case: user is inside a project folder but the CLAUDE.md is broken/missing

The be-civic skill's gate can detect this: project folder structure is there (`.be-civic-project` marker file or similar) but CLAUDE.md is missing or malformed. Offer to re-initialise the CLAUDE.md from the current plugin version, preserving user state.

### Edge case: plugin update lands a new harness version

The plugin's CLAUDE.md template is versioned (e.g., `harness/CLAUDE.md.v3`). The be-civic skill on every session start compares the version in the user's project CLAUDE.md against the latest template. If the template is newer, the skill prompts the user once: "There's an updated Be Civic harness — apply? (Recommended; your customer state is unaffected.)" On yes, it merges or replaces.

## Why this beats Pattern A (CLAUDE.md as thin pointer)

Pattern A would put a thin CLAUDE.md in the project folder that says "invoke be-civic skill on every turn" and keep the harness in the skill body. This loses the load-bearing benefit:

- **Skill bodies are loaded into context only when invoked.** A "thin pointer" CLAUDE.md doesn't change that. The harness still decays into background.
- **Skill invocation has model judgement attached.** Description triggers don't always fire on bare "hi" or non-Belgian-admin messages. The harness should be unconditionally present once inside a Be Civic project.

Pattern B puts the harness's full rules in CLAUDE.md so they're always present as system context, no skill invocation required. Peer skills become focused helpers — discovery is invoked only when there's no skill for the customer's case; path-traversal is invoked only on a `<Path>` tag — but the discipline that says "invoke them at those moments" lives in the CLAUDE.md harness.

## Why this beats the current (harness-in-skill) shape

- **Persistence.** CLAUDE.md = always on. Skill body = loaded once, drifts away.
- **User-visible state.** Project folder is a real folder on the user's machine. They can open it, browse it, back it up, share it with their lawyer. State buried in `${CLAUDE_PLUGIN_DATA}` is invisible by comparison.
- **Multi-procedure persistence by default.** A user with a nationality declaration today and an address change in six months gets both procedures' state accumulated in the same folder. No "switch to a different plugin data dir" friction.
- **Session-close auto-invocation.** The CLAUDE.md harness's terminal-step rule fires reliably because the rule is always in context. The retro's biggest miss (session-close never ran) doesn't recur.

## Open questions

1. **CLAUDE.md update strategy.** The version-comparison-and-prompt flow above is the proposed default. Alternative: never update, force users to re-onboard. Or: auto-update silently, log a change record into memory.md. **Default:** prompt-and-confirm; revisit after first 5 cross-version sessions.

2. **Project marker.** How does the be-civic skill detect "is this a Be Civic project folder"? Options: (a) read CLAUDE.md and look for a `# Be Civic` heading or known frontmatter; (b) presence of a `.be-civic-project` marker file written by onboarding; (c) presence of `profile.json` with the Be Civic schema. **Recommendation:** (b), a marker file. Cheap to check, unambiguous, survives CLAUDE.md edits.

3. **What if the user customises CLAUDE.md?** They can. The harness is theirs to edit once written. The plugin's job is to write a known-good initial version and offer a non-destructive update path when a new version of the template ships.

4. **Should the harness CLAUDE.md include things beyond Be Civic?** No. It's specifically the Be Civic harness. Cowork loads it as session context alongside any other CLAUDE.md the user has at higher levels. The harness lives at the Be Civic project root.

5. **Migration for existing testers** (people who installed the v1 plugin we shipped from `bc-operations/cowork-plugin/`). On first use of the updated plugin, the be-civic skill notices the absence of a project and offers to onboard. Their existing `${CLAUDE_PLUGIN_DATA}/...` state is offered as a one-time import into the new project folder.

## Out of scope for this design

- **GitHub feedback surface** — separate workstream (see `bc-operations/docs/2026-05-16-github-feedback-surface-feasibility.md` when complete). Backend swap, MCP surface unchanged, orthogonal to Pattern B.
- **Nationality skill content changes** — operator is taking this separately.
- **Public marketplace listing** — defer until after Pattern B ships and ~5 real-tester sessions surface friction.

## Sources

- Retrospective: `bc-operations/docs/agent-ux/sessions/2026-05-16-plugin-test/session-retrospective-2026-05-16.md` — operator-authored, end-of-session.
- Validation rules: `bc-operations/docs/agent-ux/sessions/2026-05-16-plugin-test/PLUGIN_VALIDATION_RULES.md` — empirical from the same session.
- Prior v1 plan: `~/.claude/plans/okay-i-ve-decided-that-cryptic-stroustrup.md` — what we shipped that this redesigns.
