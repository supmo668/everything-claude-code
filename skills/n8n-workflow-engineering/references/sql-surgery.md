# n8n SQL Surgery

When the n8n MCP SDK (`mcp__n8n-live__update_workflow`) refuses to fully replace a node (typically because it preserves existing `jsCode`, `modelId`, or `credentials` fields across updates), drop to direct postgres manipulation. This is the most reliable way to change workflow state.

## Schema

```
workflow_entity
├── id          — workflow ID
├── name        — display name
├── nodes       — JSON array of node definitions
├── connections — JSON object mapping node name → edges
├── settings    — JSON (executionOrder, binaryMode, availableInMCP, etc.)
└── ...
```

The `nodes` and `connections` fields are the workflow. The UI is a view over them.

## Reusable pattern — dump, mutate in Python, push back

```bash
# 1. Dump current state
docker exec n8n-postgres-1 psql -U n8n_xeos -d n8n -t -c \
  "SELECT nodes::text FROM workflow_entity WHERE id='WID';" > /tmp/nodes.json
docker exec n8n-postgres-1 psql -U n8n_xeos -d n8n -t -c \
  "SELECT connections::text FROM workflow_entity WHERE id='WID';" > /tmp/conn.json

# 2. Mutate in Python
python3 <<'PY'
import json
with open('/tmp/nodes.json') as f: nodes = json.load(f)
with open('/tmp/conn.json') as f: conns = json.load(f)

# Your mutations here
for n in nodes:
    if n['name'] == 'Target Node':
        n['parameters']['jsCode'] = "// new code"

# Rewire connections
conns['Source Node'] = {'main': [[{'node': 'Dest Node', 'type': 'main', 'index': 0}]]}

with open('/tmp/nodes_new.json','w') as f: json.dump(nodes, f)
with open('/tmp/conn_new.json','w') as f: json.dump(conns, f)
PY

# 3. Build a dollar-quoted UPDATE SQL file (sidesteps JSON-escape hell)
python3 <<'PY'
with open('/tmp/nodes_new.json') as f: nc = f.read()
with open('/tmp/conn_new.json') as f: cc = f.read()
sql = (
  f"UPDATE workflow_entity SET "
  f"nodes = $nodes${nc}$nodes$::json, "
  f"connections = $conn${cc}$conn$::json "
  f"WHERE id='WID';"
)
with open('/tmp/update.sql','w') as f: f.write(sql)
PY

# 4. Apply
docker cp /tmp/update.sql n8n-postgres-1:/tmp/update.sql
docker exec n8n-postgres-1 psql -U n8n_xeos -d n8n -f /tmp/update.sql
```

Why **dollar-quoted strings** (`$nodes$…$nodes$`) instead of `'...'`? Because the JSON contains single quotes, double quotes, backslashes, and unicode — all of which would require impossible escaping inside a standard SQL string. Postgres dollar-quoting lets you paste arbitrary binary-safe text verbatim. Pick a tag (`$nodes$`, `$conn$`, `$body$`) that's unlikely to appear in your content.

See `assets/workflow-surgery-template.py` for a ready-to-use template.

## Common mutations

**Change a Code node's jsCode:**
```python
for n in nodes:
    if n['name'] == 'My Code Node':
        n['parameters']['jsCode'] = '// new code'
```

**Rewire credentials on an OpenAI langchain node:**
```python
for n in nodes:
    if n['name'] == 'OpenAI Call':
        n['credentials'] = {'openAiApi': {'id': 'VqOZZjfmIkNbHFRp', 'name': 'OpenAI'}}
```

**Fix Google Sheets schema drift (full 8-col schema):**
```python
FULL_SCHEMA = [
  {'id': col, 'type': 'string', 'display': True, 'required': False,
   'displayName': col, 'defaultMatch': False, 'canBeUsedToMatch': True}
  for col in ['IMAGE NAME','IMAGE URL','IMAGE DESCRIPTION','CAPTION','STATUS',
              'URL VIDEO FINAL','TITRE VIDEO','CAPTION VIDEO']
]
for n in nodes:
    if n['type'] == 'n8n-nodes-base.googleSheets' and n['parameters'].get('operation') == 'appendOrUpdate':
        n['parameters']['columns']['schema'] = FULL_SCHEMA
```

**Add a field to the Config node:**
```python
for n in nodes:
    if n['name'] == 'Config: Workflow Parameters':
        existing = {a['name'] for a in n['parameters']['assignments']['assignments']}
        if 'NEW_VAR' not in existing:
            n['parameters']['assignments']['assignments'].append({
              'id': 'cfg-new-var', 'name': 'NEW_VAR', 'type': 'string',
              'value': '={{ $env.NEW_VAR }}'
            })
```

**Enable MCP on a workflow that's not accessible:**
```sql
UPDATE workflow_entity
SET settings = settings::jsonb || '{"availableInMCP":true}'::jsonb
WHERE id='WORKFLOW_ID';
```

**Retry-on-fail on an HTTP node:**
```python
for n in nodes:
    if n['name'] == 'External API Call':
        n['retryOnFail'] = True
        n['maxTries'] = 3
        n['waitBetweenTries'] = 30000  # ms
```

## Credential import (separate from workflow nodes)

n8n stores credentials in `credentials_entity`. Import via the CLI:

```bash
cat > /tmp/cred.json <<'EOF'
[
  {
    "id": "my-api-key",
    "name": "My API",
    "type": "httpCustomAuth",
    "data": { "json": "{\"headers\":{\"x-api-key\":\"...\"}}" }
  }
]
EOF
docker cp /tmp/cred.json n8n:/tmp/cred.json
docker exec n8n n8n import:credentials --input=/tmp/cred.json
```

**Gotcha:** omitting `id` fails silently with "null value in column id". Always supply an explicit `id`.

**Credential types (common):**
- `httpHeaderAuth` — single header (name + value)
- `httpCustomAuth` — arbitrary headers JSON
- `httpBasicAuth` — username + password
- `oAuth2Api` — requires UI OAuth flow; can't be fully imported
- `googleDriveOAuth2Api`, `googleSheetsOAuth2Api` — same

For OAuth credentials, you cannot fully automate import — the user must complete the OAuth handshake in the n8n UI once.

## Debugging failed executions

Execution data is stored flattened (index references) in `execution_data.data`. Not easily readable but greppable.

```bash
# Get status + timing
docker exec n8n-postgres-1 psql -U n8n_xeos -d n8n -t -c \
  "SELECT status, \"startedAt\", \"stoppedAt\" FROM execution_entity WHERE id=<N>;"

# Grep for errors
docker exec n8n-postgres-1 psql -U n8n_xeos -d n8n -t -c \
  "SELECT data::text FROM execution_data WHERE \"executionId\"=<N>;" > /tmp/exec.txt
grep -oE '"message":"[^"]{20,400}"' /tmp/exec.txt | head
grep -oE '"error_code":[0-9]+' /tmp/exec.txt
```

For deep analysis, write a Python script that parses the flattened reference list. The root runData is typically at `data[5]`; each node name in it is an index into `data[]` pointing to a list of runs. Each run is also an index ref. Recursively resolve with a visited-set to avoid cycles.

## Danger zones

- **Foreign keys:** `workflow_entity.id` is referenced by `execution_entity`, `workflow_statistics`, etc. Don't delete workflows casually.
- **Concurrent runs:** if an execution is currently running, its state is in `execution_entity` with `status='running'` or `'waiting'`. Mutating `workflow_entity.nodes` while a run is in flight is safe (n8n reads the workflow at execution-start), but confusing for debugging.
- **Backup first:** before bulk mutations, `pg_dump workflow_entity > backup.sql`. You can restore a single row with `COPY workflow_entity FROM ...`.
