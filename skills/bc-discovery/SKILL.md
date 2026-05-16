---
name: bc-discovery
description: Use when Be Civic has no verified skill for the customer's procedure (skill mode) or no verified path for a needed source (path mode). Walks the customer through with research-as-we-go discipline. Produces a durable research-notes file the drafter consumes at session close.
---

# Be Civic — Discovery

Two modes:

- **`skill` mode** — fires on graph zero-match for the customer's intent, or when `bc-path-traversal` returns `unknown-skill-fallback`.
- **`path` mode** — fires when `bc-path-traversal` returns a structured miss signal (`unknown-path-id` or `all-sources-failed-with-alternative`).

The framing matters: **this is "discovery mode," not "no-skill fallback."** First use of the term in a session MUST carry a gloss; the bare phrase is fine thereafter (CLAUDE.md §16 jargon rule).

## 1. Opening

**Skill mode:**

> "Be Civic doesn't have a verified procedure for [name the procedure] yet — so let's switch to discovery mode (where we walk through this together and document what we find for the next person filing the same thing). I'll ask you what you know, look up what I can verify, and keep notes as we go. You get help with your procedure today; the next person filing this hits a verified skill instead of a blank."

**Path mode:**

> "We needed [path name / source] for this step, and Be Civic doesn't have a verified path entry yet. Let's switch to discovery mode (same idea — we walk it together and document what works). I'll log every source I can verify and we'll see where it lands."

Don't preamble the contribution framing every turn after that — once is enough (CLAUDE.md §14 voice rule).

## 2. Source-quality discipline

Citation-grade only for claims that end up in canonical:
- Belgian statute, federal regulation, regional decree.
- Federal / regional / commune official pages (`*.belgium.be`, `*.brussels`, `*.vlaanderen.be`, `*.wallonie.be`, `*.<commune>.be`).
- Professional-body guidance (notary, lawyer, sworn translator).
- Origin-country government sites for foreign documents.

**Signal-only** sources (forum posts, news articles, expat blogs, Reddit) may be read freely to find a trail but are NEVER cited in research-notes as evidence. They are scaffolding, not citation.

## 3. Research-as-we-go

WebFetch authoritative sources as questions come up. Never invent procedural detail. If you can't verify a claim:
- Mark it as `[customer-report: <date>]` and keep going — the drafter may still propose the skill with that point flagged as `verify-with-commune`.
- Or surface to the customer and ask whether they have a source we can WebFetch.

Cite every claim with: URL + date-fetched + verbatim snippet (≤300 chars per snippet). If a page is gated or 404s, log it as `[citation_404: <url>]` so the next session knows not to retry.

## 4. Sub-skill detection

If a sub-step in the discovery walk is covered by an existing Be Civic skill (e.g. apostille for a foreign birth certificate, EU 2016/1191 multilingual form), Load that skill via the Skill tool and walk it normally. In research-notes, mark those segments `[verified-corpus: <skill_id> v<version>]` rather than re-deriving the procedure.

## 5. Research-notes file (the durable artefact)

Write to `memory/research-notes-<slug>.md`. Slug is kebab-case of the procedure name (skill mode) or path id (path mode), truncated to ≤32 chars. Frontmatter:

```yaml
---
kind: discovery_session
target_type: skill | path
target_slug: <slug>
status: in_progress | ready_to_draft | drafted | discarded
first_session_at: <ISO8601>
last_session_at: <ISO8601>
session_count: <int>
verified_corpus_refs: [<skill_id>, ...]
research_sources:
  - url: <url>
    kind: citation-grade | signal-only
    claim: <≤200 chars>
    fetched_at: <ISO8601>
---
```

Body: prose with tagged claims. Every claim carries one of:
- `[verified-corpus: <id>]` — covered by an existing skill walk.
- `[citation: <url>]` — verified against a citation-grade source we WebFetched.
- `[customer-report: <date>]` — customer told us; not independently verified.
- `[verify-with-commune]` — needs a commune visit or appointment to confirm.

The drafter at session close reads this file and produces a `skill_draft` (or `path_draft`) submission with `provenance.research_notes_markdown` set to this file's body. The CC BY 4.0 grant the customer makes at submission covers both canonical and research-notes jointly (lifecycle.md §9.6).

## 6. Status transitions

- `in_progress` — active session, more to learn.
- `ready_to_draft` — the customer says they've done the procedure or has enough verified claims to propose a skill. Set when the customer agrees in plain language. Picked up by next session's pending-state scan, surfaced at `bc-session-close` for drafter handoff.
- `drafted` — set by session-close after the drafter has produced and the customer has approved a submission.
- `discarded` — customer abandoned; file kept locally but not surfaced again.

## 7. Resume marker on the profile

Add `discovery:skill:<slug>` or `discovery:path:<slug>` to `profile.json` `active_procedures` so a returning session resumes correctly. Remove on `drafted` or `discarded` transition.

## 8. Exit

Discovery exits when:
- The customer says they're done for now (status `in_progress`, resume next session).
- The customer says they've finished the procedure (status `ready_to_draft`, session-close offers drafter handoff).
- The customer abandons (`discarded`).

## What this skill does NOT own

- Drafting the canonical or path entry. That's the `bc-skill-drafter` / `bc-path-drafter` subagent's job, spawned from `bc-session-close` after customer approval.
- Submitting anything. Submission is gated by per-item review at session close.
- Producing volatile-value catalogue rows. Discovery records them in research-notes; the drafter decides whether they become `<VV>` rows.
