# Substrate-contract test rig — W31.7a/b/c

Integration gate for the 40-substrate contract. Three test surfaces:

| File | Sprint item | Purpose |
|---|---|---|
| `test_substrate_contract.py` | W31.7a | Verifies the 8-node state graph, atomic-commit, and two-surface layout against any substrate implementation. Run after W33, W35, W37 as the integration gate. |
| `../stubs/cowork-stub.py` | W31.7b | Cowork stub harness — sets up the two-surface layout under `~/.be-civic-stub/`, stubs `mcp__cowork__request_cowork_directory` and `mcp__visualize__show_widget`. |
| `test_v1_v2_compat.py` | W31.7c | V1 plugin against V2 API via deprecation aliases. Sprint-close dogfood gate. |

## Quick start

### W31.7b — Set up Cowork stub harness

```bash
# Create the two-surface substrate layout under ~/.be-civic-stub/
python3 stubs/cowork-stub.py --setup

# Print env-var assignments and activate in current shell
eval "$(python3 stubs/cowork-stub.py --show-env)"

# Confirm: $CLAUDE_PLUGIN_DATA and $CLAUDE_PLUGIN_DATA_VISIBLE are set
echo "STATE:   $CLAUDE_PLUGIN_DATA"
echo "VISIBLE: $CLAUDE_PLUGIN_DATA_VISIBLE"
```

### W31.7a — Run substrate-contract tests

```bash
# Against stub harness defaults (~/.be-civic-stub/)
python3 tests/substrate-contract/test_substrate_contract.py --stub

# Against explicit paths
python3 tests/substrate-contract/test_substrate_contract.py \
    --substrate-data  /path/to/BeCivic \
    --substrate-state /path/to/plugin-data \
    --substrate-root  /path/to/plugin-root
```

Expected output (fresh stub):

```
=== 40-substrate contract verification ===
  SUBSTRATE_DATA:  ~/.be-civic-stub/BeCivic
  SUBSTRATE_STATE: ~/.be-civic-stub/plugin-data

§10 Substrate prerequisites
  ok   ${SUBSTRATE_DATA} and ${SUBSTRATE_STATE} are distinct paths
  ok   ${SUBSTRATE_STATE} is writable
  ok   ${SUBSTRATE_DATA} is writable
...
15 passed, 0 failed, 1 skipped
```

### W31.7c — V1→V2 API compatibility dogfood

```bash
# Against production (read-only endpoints — no harness key needed)
python3 tests/substrate-contract/test_v1_v2_compat.py \
    --base-url https://becivic.be

# With harness key (all endpoints including submission dry-run)
python3 tests/substrate-contract/test_v1_v2_compat.py \
    --base-url https://becivic.be \
    --harness-key $HARNESS_KEY

# Against local dev worker
python3 tests/substrate-contract/test_v1_v2_compat.py \
    --base-url http://localhost:8787 \
    --skip-submit
```

## Sprint-close gate procedure (W33, W35, W37)

Run these three commands at sprint close. All three must exit 0:

```bash
# 1. Substrate contract
python3 tests/substrate-contract/test_substrate_contract.py --stub

# 2. V1→V2 compat
python3 tests/substrate-contract/test_v1_v2_compat.py --base-url https://becivic.be

# 3. Validate-cross-refs (bc-knowledge-graph CI check)
cd ../bc-knowledge-graph && npx tsx tools/scripts/validate-cross-refs.ts
```

## Design notes

**Stdlib only.** All test scripts use only Python stdlib — no pytest, no requests,
no third-party deps. The tests must run inside any substrate execution context
(Cowork plugin runtime, Cowork stub, bare terminal).

**Explicit stub signalling.** Every stub call prints `[STUB_ACTIVE: <mcp-tool-name>]`
so the operator knows what is and is not native Cowork behaviour. This is a firm
requirement from the sprint spec.

**Spec refs.**
- `bc-workspace/handbook/content/05-product/40-substrate.md` — substrate contract
- `bc-workspace/handbook/content/05-product/51-cowork.md` — Cowork binding
- `bc-workspace/handbook/content/04-domain/04-substrate-state.md` — 8-node state graph
- `bc-workspace/roadmap/sprints/2026-W31-v2-api-and-auth.md` §Phase7 — sprint spec
