---
name: n8n-workflow-dev-debug
description: "Develop and debug self-hosted n8n workflows — iterate on Code-node logic, HTTP Request nodes, and Set/IF/Merge wiring; diagnose failing executions by pulling flat execution_data from postgres and resolving the reference graph; preserve the user's hand-tuned canvas layout on every edit; apply minimal-diff surgery so visual rearrangements survive. USE THIS SKILL whenever the user is developing, iterating on, or debugging an n8n workflow — running test executions, inspecting exec errors, editing Code nodes, or adjusting connections. Also use when the user mentions 'the workflow broke', 'exec 123 failed', 'node X didn't fire', or pastes an n8n execution URL. Complements `n8n-workflow-engineering` (which covers broader architecture, credentials, and integrations); this skill is specifically about the tight dev/debug loop."
origin: ECC
---

# n8n Workflow Dev & Debug

The tight feedback loop of *edit → execute → inspect → fix* on self-hosted n8n. This skill is for the minute-to-minute work of moving a workflow from "errored" to "green."

## When to use

- Iterating on Code node logic after an exec failure
- Diagnosing why a specific execution errored (`executionId`, `lastNodeExecuted`, stack trace)
- Editing HTTP Request, Set, IF, Merge, or Wait nodes to correct flow/data issues
- Adjusting connections (adding a Merge, splitting a fan-out, rewiring after a node swap)
- Verifying a fix end-to-end after surgery
- Preserving the user's manual canvas layout across edits

For system-level architecture (credentials, env plumbing, integrations, the Config-node pattern), use `n8n-workflow-engineering`. This skill trusts that structure is already in place.

## Core dev loop

```
1. Reproduce      — trigger the workflow; capture executionId
2. Diagnose       — pull exec data, find lastNodeExecuted + error message
3. Isolate        — identify which node/field/expression is wrong
4. Edit           — minimal-diff change (mutate in place, don't rebuild)
5. Verify         — re-trigger; confirm the target node and downstream all run
```

Short iterations. Don't batch 5 fixes into one run — if something still fails, you won't know which fix broke it.

## Canvas layout is user-owned

Every node has `position: [x, y]` driving its canvas placement. When a human drags nodes around for readability, those coordinates change. **Your edits must preserve them.**

1. **Modifying an existing node** (change `jsCode`, swap a credential, add a parameter): never touch `position`. Mutate in place:
   ```python
   for n in nodes:
       if n['name'] == 'My Code Node':
           n['parameters']['jsCode'] = NEW_CODE   # mutate only this field
   ```
   Do **not** rebuild the node from scratch — you'll clobber the user's layout.

2. **Replacing a node** (change type, swap for a semantically different node): copy `position` from the replaced node onto the new one. Graph topology matters; coordinates don't.

3. **Adding a brand-new node**: anchor relative to a logical neighbor. n8n's canvas grid is ~176-192px horizontal between columns and ~64-144px vertical between rows. Drop the new node ~192px right of whatever feeds it.

4. **After any surgery, diff positions** on existing nodes. If anything unexpectedly moved, restore before pushing. See `references/layout-preservation.md` for ready-made helpers (`replace_node_preserving_position`, `positions_diff`, `restore_positions`).

Treat the user's repositioning as source-of-truth. If they moved nodes between agent edits, that layout wins.

## Reproducing a failure

```bash
# Trigger a manual execution via MCP or the UI
# Get the execution id (e.g., 206)

# Status check
docker exec n8n-postgres-1 psql -U n8n_xeos -d n8n -t -c \
  "SELECT status, \"startedAt\", \"stoppedAt\", \"waitTill\" FROM execution_entity WHERE id=206;"

# If status = 'waiting' and waitTill is in the future: it's in a Wait node; come back later
# If status = 'error': proceed to diagnose
```

## Diagnosing execution data

n8n stores execution data in `execution_data.data` as a **flattened reference array** — a single JSON list where objects reference each other by index string (e.g., `"5"` means "the object at data[5]"). It's awful to read by hand, fine to grep.

### Fast path: grep for the error string

```bash
docker exec n8n-postgres-1 psql -U n8n_xeos -d n8n -t -c \
  "SELECT data::text FROM execution_data WHERE \"executionId\"=206;" > /tmp/exec.txt

# Common patterns
grep -oE '"message":"[^"]{20,400}"' /tmp/exec.txt | head
grep -oE '"error_code":[0-9]+' /tmp/exec.txt
grep -oE '"httpCode":"[0-9]+"' /tmp/exec.txt
grep -oE '"reason":"[a-z_]+"' /tmp/exec.txt
```

### Resolve the runData structure

```python
import json
data = json.load(open('/tmp/exec.txt'))   # top-level is a list of flat entries

def resolve(x, seen=None, depth=40):
    if seen is None: seen = set()
    if depth <= 0: return None
    if isinstance(x, str) and x.isdigit():
        i = int(x)
        if i in seen or i >= len(data): return None
        return resolve(data[i], seen | {i}, depth - 1)
    if isinstance(x, dict): return {k: resolve(v, seen, depth - 1) for k, v in x.items()}
    if isinstance(x, list): return [resolve(v, seen, depth - 1) for v in x]
    return x

# runData typically lives at data[5]
runData = data[5]
for node_name, run_ref in runData.items():
    runs = data[int(run_ref)] if isinstance(run_ref, str) and run_ref.isdigit() else run_ref
    if isinstance(runs, list) and runs:
        first = resolve(data[int(runs[0])] if isinstance(runs[0], str) else runs[0])
        status = first.get('executionStatus', '?') if first else '?'
        print(f'{node_name}: status={status}')
```

### The MCP `get_execution` shortcut

If `mcp__n8n-live__get_execution` is available, prefer it — you get a structured, resolved view. But it sometimes chokes on circular references (HTTP node's `_httpMessage` → `res` → etc.). When that happens, fall back to postgres + resolve().

## Common failure modes & fixes

| Symptom | Likely cause | Fix |
|---|---|---|
| `fetch is not defined [line N]` | Code node tried to use browser `fetch` | Use `this.helpers.httpRequest` instead — see `n8n-workflow-engineering` reference |
| `$helpers is not defined` | Wrong global name | `const helpers = this.helpers;` |
| Code node returns instantly (<100ms) when a loop should take minutes | Task-runner timeout (default 60s) killed it silently | Set `N8N_RUNNERS_TASK_TIMEOUT=600` in docker-compose; use Submit → Wait → Poll pattern |
| `Column names were updated after the node's setup` | Google Sheets node schema drift | Update the node's `parameters.columns.schema` to match the sheet's current columns |
| `Credentials not found` | Credential referenced by id/name doesn't exist in n8n | Create via `docker exec n8n n8n import:credentials --input=<file>` (always supply explicit `id`) |
| `Node 'X' hasn't been executed` in expression | Referenced node is on a branch that didn't fire, or parallel fan-in caused a race | Serialize the chain (A → B → Agg) or use a Merge node |
| `The value in the "JSON Body" field is not valid JSON` | Expression returned `undefined`/empty | Upstream node didn't emit expected data; check that node's output |
| 429 RESOURCE_EXHAUSTED | Per-minute rate limit OR daily quota | Add exponential backoff (45s+) with sequential submits; on persistent 429, switch model variant or wait |
| Workflow "succeeds" but no output | Early branch termination, SKIP path forgot to merge, or silent Code-node error | Walk the connections graph; confirm the expected final node is reachable from the executed path |
| Telegram `Bad Request: failed to get HTTP URL content` | Telegram can't fetch the URL (Drive auth-wall, expired URL, etc.) | Download via HTTP node then use `binaryData: true`, or send as text instead |

## Editing nodes — minimal-diff discipline

**Rule: patch the specific fields you changed; everything else stays identical.**

```python
# Good — mutate in place
for n in nodes:
    if n['name'] == 'Target Node':
        n['parameters']['jsCode'] = NEW_CODE
        n['credentials'] = {'openAiApi': {'id': 'NEW_ID', 'name': 'OpenAI'}}

# Bad — rebuild from scratch (loses position, webhookId, onError, retryOnFail, etc.)
nodes = [n for n in nodes if n['name'] != 'Target Node'] + [{
    'id': str(uuid.uuid4()),
    'name': 'Target Node',
    'type': 'n8n-nodes-base.code',
    'position': [1920, 1040],   # <- overwrites user's manual layout
    'parameters': {'jsCode': NEW_CODE}
    # ... missing credentials, onError, webhookId, alwaysOutputData, etc.
}]
```

### When you actually need to replace a node

Use `replace_node_preserving_position()` — copies `position` and `webhookId` from the old node onto the new one. Source at `references/layout-preservation.md`.

## Rewiring connections

Each node name in `workflow_entity.connections` maps to `{main: [[...edges...]]}`. Common edits:

```python
# Add an edge: Source → NewTarget
conns['Source'] = {'main': [[{'node': 'NewTarget', 'type': 'main', 'index': 0}]]}

# Multi-target fan-out
conns['Source'] = {'main': [[
    {'node': 'Target A', 'type': 'main', 'index': 0},
    {'node': 'Target B', 'type': 'main', 'index': 0},
]]}

# IF node (two outputs: TRUE, FALSE)
conns['My IF'] = {'main': [
    [{'node': 'True Path', 'type': 'main', 'index': 0}],
    [{'node': 'False Path', 'type': 'main', 'index': 0}],
]}

# Terminate a branch (SKIP path shouldn't rejoin PROCEED)
conns['Slack: Duplicate'] = {'main': [[]]}   # empty branch

# Remove stale edges after deleting a node
for src, val in list(conns.items()):
    val['main'] = [[e for e in branch if e['node'] != 'Deleted Node'] for branch in val.get('main', [])]
```

After connection edits, re-inspect the graph:
```bash
docker exec n8n-postgres-1 psql -U n8n_xeos -d n8n -t -c \
  "SELECT connections::text FROM workflow_entity WHERE id='WID';" | python3 -c "
import sys, json
c = json.load(sys.stdin)
for src, val in c.items():
    tgts = [e['node'] for branch in val.get('main', []) for e in branch]
    print(f'  {src:50s} → {\", \".join(tgts) or \"(end)\"}')"
```

## Verifying a fix

After every surgical change:

1. Trigger a fresh execution manually.
2. Check `status` on `execution_entity` — `success`, `error`, or `waiting`.
3. If `success`: confirm the target node's output has the expected shape.
4. If `error`: pull exec data, compare `lastNodeExecuted` and error message to your prior diagnosis. If it's the same error, your fix didn't take — check that SQL UPDATE actually hit the right field (`docker exec n8n-postgres-1 psql ... -c "SELECT nodes::text FROM workflow_entity WHERE id='WID';"` + grep for your change).
5. If a DIFFERENT error: great, progress. Diagnose and iterate.

**Don't declare a fix complete until the full execution succeeds end-to-end.** Mid-flow success on one node doesn't mean the downstream path works.

## Cost awareness during debug

Some nodes burn money on every run. Before re-triggering a full workflow:

- **Veo 3.x** ~$0.50 per clip. Multi-scene pipelines compound. If the bug is before the Veo nodes, test a truncated flow (pin earlier data, start from the problematic node) — don't re-burn Veo just to validate a fix in a downstream Code node.
- **JSON2Video / Creatomate** — monthly render quota; keep payloads minimal during debug.
- **OpenAI vision / chat** — cheap but add up.
- **Free-tier LLMs / image APIs** — often have daily limits that kick in mid-debug session.

When possible, **pin execution data** on the node just upstream of your target and trigger from there. Avoid the full pipeline re-run for single-node fixes.

## References

- `references/layout-preservation.md` — ready-made helpers: `replace_node_preserving_position`, `positions_diff`, `offset_from`, `restore_positions`
- `references/exec-data-parsing.md` — deeper guide to the flattened `execution_data` format
- `n8n-workflow-engineering` skill — architecture, credentials, integrations, Code node sandbox capabilities, SQL surgery details
