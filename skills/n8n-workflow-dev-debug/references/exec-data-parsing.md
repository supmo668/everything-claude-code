# Parsing n8n execution_data

n8n stores every execution's runtime data in `execution_data.data` as a JSON string that, when parsed, returns a **flattened array** where entries reference each other by string indices. This dramatically reduces storage size by deduping shared objects — and makes it miserable to read by hand. Here's how to work with it.

## The flat-reference format

```json
[
  /* [0] */ { "version": 1, "startData": "1", ... },
  /* [1] */ {},
  /* [2] */ { "runData": "5", "pinData": {} },
  /* [3] */ ...
  /* [5] */ { "Poll Every 5 Min": "6", "Telegram: Poll Updates": "7", ... },
  /* [6] */ [ "8" ],                            // list of runs for that node
  /* [7] */ [ "12" ],
  /* [8] */ { "startTime": "9", "executionStatus": "10", "data": "11" },
  /* [10] */ "success",
  ...
]
```

Any string that parses as an integer is an index into `data[]`. Recursive resolution is required to get back to the canonical tree.

## Resolving to a readable tree

```python
import json

data = json.load(open('/tmp/exec.txt'))

def resolve(x, seen=None, depth=40):
    """Walk a flattened n8n execution_data list, resolving indexed references into nested dicts/lists.
    Guards against cycles (seen set) and pathological depth (hard cap)."""
    if seen is None: seen = set()
    if depth <= 0: return None
    if isinstance(x, str) and x.isdigit():
        i = int(x)
        if i in seen or i >= len(data): return None
        return resolve(data[i], seen | {i}, depth - 1)
    if isinstance(x, dict):
        return {k: resolve(v, seen, depth - 1) for k, v in x.items()}
    if isinstance(x, list):
        return [resolve(v, seen, depth - 1) for v in x]
    return x
```

## Common queries

### What was the last node executed?

```python
for entry in data:
    if isinstance(entry, dict) and 'lastNodeExecuted' in entry:
        last = entry['lastNodeExecuted']
        if isinstance(last, str) and last.isdigit():
            last = data[int(last)]
        print('last:', last)
        break
```

### Which nodes ran successfully, which errored?

```python
# runData is usually at data[5]; verify by checking it's a dict whose keys are node names
run = data[5]
for node_name, runs_ref in run.items():
    runs = data[int(runs_ref)] if isinstance(runs_ref, str) and runs_ref.isdigit() else runs_ref
    if isinstance(runs, list) and runs:
        first = resolve(data[int(runs[0])] if isinstance(runs[0], str) else runs[0])
        status = first.get('executionStatus', '?') if first else '?'
        print(f'{node_name}: {status}')
```

Status values (as strings) live somewhere in data[] — often `'success'`, `'error'`, `'running'`. `executionStatus` references one by index.

### Output of a specific node

```python
run = data[5]
if 'MyNode' in run:
    idx = int(run['MyNode'])
    runs = data[idx]
    first = resolve(data[int(runs[0])] if isinstance(runs[0], str) else runs[0])
    # data.main[0] is the list of output items from the first run
    out_items = (first.get('data', {}) or {}).get('main', [[]])[0]
    for item in out_items:
        print(item.get('json'))
```

### The full error object

```python
# Errors are typically near position 17ish or grep'd directly
for i, e in enumerate(data):
    if isinstance(e, str) and 'Error' in e and 20 < len(e) < 500:
        print(f'[{i}] {e}')
```

Or walk `runData[lastNodeExecuted].error`:

```python
run = data[5]
last = None
for entry in data:
    if isinstance(entry, dict) and 'lastNodeExecuted' in entry:
        last_ref = entry['lastNodeExecuted']
        last = data[int(last_ref)] if isinstance(last_ref, str) and last_ref.isdigit() else last_ref
        break
if last and last in run:
    last_idx = int(run[last])
    first_run = resolve(data[int(data[last_idx][0])])
    err = first_run.get('error')
    if err:
        print(json.dumps(err, indent=2)[:800])
```

## Grep-only debugging (no python)

For quick triage, raw grep is often enough:

```bash
# the text
docker exec n8n-postgres-1 psql -U n8n_xeos -d n8n -t -c \
  "SELECT data::text FROM execution_data WHERE \"executionId\"=<N>;" > /tmp/exec.txt

# human-readable error strings
grep -oE '"message":"[^"]{20,400}"' /tmp/exec.txt | head
grep -oE '"description":"[^"]{20,400}"' /tmp/exec.txt | head

# HTTP errors
grep -oE '"httpCode":"[0-9]+"' /tmp/exec.txt
grep -oE '"error_code":[0-9]+' /tmp/exec.txt | sort -u

# last executed + status strings
grep -oE '"lastNodeExecuted"[^"]*"[^"]+"' /tmp/exec.txt
grep -oE '"executionStatus"[^"]*"[^"]+"' /tmp/exec.txt | sort -u
```

## Gotchas

- **Don't trust `executionTime`** on a run record — if the task-runner timed out, n8n may record a short time even though the node actually hung for 60+ seconds. Compare `startedAt` vs `stoppedAt` on `execution_entity` for true wall-clock.
- **Circular refs**: HTTP Request node responses can contain internal socket objects (`_httpMessage` → `res` → `_httpMessage` → ...). MCP `get_execution` sometimes fails to JSON-serialize these with `"Converting circular structure to JSON"` — fall back to postgres + grep.
- **Canceled/waiting executions have partial data**: not all nodes will have runs; `runData` may be missing some keys.
- **pairedItem is a separate axis**: when looking at iteration (fan-out) data, each item has `.pairedItem.item` pointing back to its index in the emitting node's output list. Use this to reconstruct which input produced which output.
- **Flat list length varies wildly**: a trivial exec may have 30-80 entries; a multi-scene pipeline with Drive uploads can hit 1000+. Don't bail on size — the resolve function handles any depth.

## When to just use the n8n UI instead

If the error is visible in the n8n web UI's execution viewer, READ IT THERE. It's slower to navigate but renders the data tree natively. Use postgres parsing when:
- You're writing tooling/skill automation
- The UI is down or not accessible
- You need machine-readable diffs across runs
- The MCP `get_execution` is choking on circular refs
