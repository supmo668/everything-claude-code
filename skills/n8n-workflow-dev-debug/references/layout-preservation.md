# Preserving canvas layout during surgery

Ready-to-drop-in Python helpers for mutating an n8n workflow without clobbering `position` fields. The humans who rearrange the canvas for readability expect their layout to survive the next round of edits.

## When each helper applies

| Situation | Helper | What it does |
|---|---|---|
| Update `jsCode`, swap a credential, tweak a parameter | No helper needed | Just mutate the specific field in place (`n['parameters']['jsCode'] = NEW`); `position` is left alone |
| Replace a node (new `type`, same graph position) | `replace_node_preserving_position()` | Copies `position` + `webhookId` from the old node onto the new one |
| Add a brand-new node next to an existing one | `offset_from()` | Anchors coordinates on a logical neighbor |
| After any bulk edit | `positions_diff()` | Reports layout drift on existing nodes |
| Recover layout after a wholesale rebuild | `restore_positions()` | Copies positions from a pre-edit snapshot onto matching nodes in the new list |

## The helpers

```python
def replace_node_preserving_position(nodes: list, old_name: str, new_node: dict) -> dict:
    """Swap the node named old_name for new_node. Keeps the old node's position
    and webhookId (if the new node doesn't specify one). Returns the replacement.
    Raises KeyError if old_name not found."""
    for i, n in enumerate(nodes):
        if n["name"] == old_name:
            new_node = dict(new_node)  # shallow copy; don't mutate caller's dict
            new_node["position"] = list(n.get("position", new_node.get("position", [0, 0])))
            if "webhookId" in n and "webhookId" not in new_node:
                new_node["webhookId"] = n["webhookId"]
            nodes[i] = new_node
            return new_node
    raise KeyError(f"No node named {old_name!r}")


def offset_from(nodes: list, anchor_name: str, dx: int = 192, dy: int = 0) -> list:
    """Return [x, y] offset from the anchor node's position.
    n8n canvas grid ≈ 176-192px horizontal columns, 64-144px vertical rows.
    Typical uses:
        offset_from(nodes, 'Upstream', dx=192)           # one column right
        offset_from(nodes, 'Upstream', dy=128)           # one row below
        offset_from(nodes, 'Upstream', dx=192, dy=128)   # diagonal"""
    for n in nodes:
        if n["name"] == anchor_name:
            p = n.get("position", [0, 0])
            return [int(p[0]) + dx, int(p[1]) + dy]
    raise KeyError(anchor_name)


def positions_diff(before_nodes: list, after_nodes: list) -> dict:
    """Return {name: (before_pos, after_pos)} for existing nodes whose position
    changed. Call after mutation to flag unintended layout shifts."""
    bpos = {n["name"]: tuple(n.get("position", [])) for n in before_nodes}
    shifted = {}
    for n in after_nodes:
        name = n["name"]
        if name in bpos and tuple(n.get("position", [])) != bpos[name]:
            shifted[name] = (bpos[name], tuple(n.get("position", [])))
    return shifted


def restore_positions(nodes: list, snapshot: list) -> int:
    """Copy positions from snapshot onto nodes with matching names.
    Useful if you rebuilt the whole nodes list and want to rescue the user's
    layout for nodes that still exist. Returns the number restored."""
    spos = {n["name"]: list(n.get("position", [])) for n in snapshot}
    count = 0
    for n in nodes:
        if n["name"] in spos:
            n["position"] = list(spos[n["name"]])
            count += 1
    return count
```

## Usage

```python
import copy
import json
import subprocess

# Dump the current workflow
def pg_get(q):
    return subprocess.run(
        ["docker", "exec", "n8n-postgres-1", "psql", "-U", "n8n_xeos", "-d", "n8n", "-t", "-c", q],
        capture_output=True, text=True, check=True
    ).stdout.strip()

nodes = json.loads(pg_get("SELECT nodes::text FROM workflow_entity WHERE id='WID';"))
conns = json.loads(pg_get("SELECT connections::text FROM workflow_entity WHERE id='WID';"))

# Snapshot for layout drift detection
snapshot = copy.deepcopy(nodes)

# --- Case 1: modify in place (no helper needed) ---
for n in nodes:
    if n["name"] == "My Code Node":
        n["parameters"]["jsCode"] = "// new logic"

# --- Case 2: replace a node, keep position ---
replace_node_preserving_position(nodes, "Old Sheets Node", {
    "id": "new-uuid",
    "name": "New Notion Node",
    "type": "n8n-nodes-base.notion",
    "typeVersion": 2.2,
    "parameters": { ... },
    "credentials": { ... },
})

# --- Case 3: add a new node near a neighbor ---
nodes.append({
    "id": "another-uuid",
    "name": "Extra Validation",
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": offset_from(nodes, "My Code Node", dx=192),
    "parameters": { "mode": "runOnceForAllItems", "language": "javaScript",
                    "jsCode": "// check stuff" }
})

# --- Before push: flag unintended drift ---
moved = positions_diff(snapshot, nodes)
if moved:
    print(f"⚠ {len(moved)} existing nodes shifted:")
    for name, (b, a) in moved.items():
        print(f"    {name}: {b} -> {a}")
    # Optional: restore_positions(nodes, snapshot) to revert

# Push back with dollar-quoted SQL (see n8n-workflow-engineering/sql-surgery.md for pattern)
```

## When NOT to preserve layout

- User explicitly asked for a graph restructure ("move the Veo chain above the Notion chain")
- You added so many new nodes that the old layout is incoherent — tell the user, let them tidy
- A bulk find/replace across the whole graph where individual positions were never meaningful

In all other cases: preserve. Canvas layout carries *information* — grouping, reading order, visual hierarchy — that the user put there deliberately.
