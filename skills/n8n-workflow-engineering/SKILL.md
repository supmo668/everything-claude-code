---
name: n8n-workflow-engineering
description: "Build, modify, and debug self-hosted n8n workflows — Config-node/env pattern, SQL-level surgery on workflow state, Code node sandbox quirks (this.helpers.httpRequest), long-operation Submit→Wait→Poll architecture, per-item binary iteration (HTTP download → Drive/S3 upload → aggregate), resilient polling for generative APIs (RAI filters, internal errors, timeouts), credential 4-location management (Infisical + .env + docker + n8n UI), and integrations with Veo 3.0/3.1, JSON2Video, Creatomate, Telegram, Google Drive/Sheets. USE THIS SKILL whenever the user touches n8n — building new pipelines, debugging failing executions, editing nodes via SDK or postgres surgery, managing credentials, wiring generative-media APIs, or diagnosing rate-limit/quota/sandbox errors, even if they just say 'my workflow is broken' without mentioning n8n by name. Also use when the task involves a Telegram trigger, Google Sheets upsert, fal.ai/Veo/JSON2Video HTTP integration, or orchestrating multi-scene AI video generation, since all of those patterns live in this skill."
origin: ECC
---

# n8n Workflow Engineering

Practical patterns for authoring, patching, and validating self-hosted n8n workflows. Every pattern here came from a real failure — treat each section as a landmine already stepped on.

## When to use

- Creating a new n8n workflow (Telegram trigger, scheduled job, multi-scene media pipeline, etc.)
- Modifying an existing workflow — especially when the n8n MCP SDK won't fully replace nodes or silently preserves old fields
- Debugging Code nodes that fail with `fetch is not defined`, `$helpers is not defined`, task-runner timeouts, or `Column names were updated after the node's setup`
- Wiring long-running external APIs (Veo 3.x, JSON2Video, Creatomate, HeyGen, ElevenLabs, fal.ai)
- Managing credentials across Infisical, `.env`, docker-compose, and n8n's UI
- Choosing between parallel and sequential API calls under rate-limits
- Building per-item iteration pipelines (download binary → cloud upload → aggregate)

## Core mental model

An n8n workflow is two JSON documents in postgres: `nodes` (array of node defs) and `connections` (graph). Everything the n8n UI shows is a view over these two fields. When the SDK misbehaves (update_workflow preserves stale params, credentials auto-assign wrong, node references don't update), drop to **SQL surgery** — dump, mutate in Python, push back with a dollar-quoted `UPDATE`. It always works.

Node execution happens in a **task-runner sandbox** with a hard default 60s timeout (`N8N_RUNNERS_TASK_TIMEOUT`). Long synchronous loops (polling external APIs for minutes) don't fit there — split into `Submit → Wait → Poll` where the heavy wait lives in a `Wait` node that persists execution state to the DB.

Per-item iteration is a first-class pattern: a Code node that returns N items fans out to downstream nodes (each fires once per item), and a final `runOnceForAllItems` Code node aggregates. Use `pairedItem.item` to rejoin downstream outputs with original metadata since downstream nodes often overwrite incoming `$json` fields.

## The Config-node/env pattern

All workflow-wide IDs, URLs, and API keys live in a single `Config: Workflow Parameters` Set node that reads from `$env.*`. Secrets flow: **Infisical (source) → `.env` (mirror) → docker-compose env passthrough → `$env` → Config node → all downstream nodes via `$('Config: Workflow Parameters').item.json.X`**.

This keeps secrets out of workflow JSON (safe to export) and gives you one place to change any parameter. To add a new env-driven field: add a `boolean`/`string` assignment to the Config Set node whose value is `={{ $env.NEW_VAR }}`, then reference downstream via `$('Config: Workflow Parameters').item.json.NEW_VAR`. Don't forget to add `- NEW_VAR=${NEW_VAR}` in `docker-compose.*.yml` under `services.n8n.environment` — without the passthrough, `$env.NEW_VAR` is `undefined` inside the container.

Critical setting: `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`. Without it every `$env` expression throws "access to env vars denied".

## Credentials — 4-location rule

Every secret lives in all 4 of these locations; any of them out-of-sync causes a runtime failure:

1. **Infisical** (source of truth) — `mcp__infisical__create-secret` with the project ID and `environmentSlug: prod`
2. **`.env`** at the n8n project dir (mirror of Infisical, ignored by git)
3. **`docker-compose.*.yml`** under `services.n8n.environment` — `- API_KEY=${API_KEY}`
4. **n8n UI credential store** — only needed if the node uses `authentication: genericCredentialType` (e.g., OAuth, httpHeaderAuth, httpCustomAuth). Create via `docker exec n8n n8n import:credentials --input=<file>` with an explicit `id` in the JSON (omitting id fails silently)

When the node can accept an arbitrary header (most HTTP requests to third-party APIs), **prefer env-based header injection** over UI credentials — one fewer artifact to manage:
```yaml
sendHeaders: true
headerParameters:
  parameters:
    - name: x-api-key
      value: "={{ $('Config: Workflow Parameters').item.json.API_KEY }}"
```

## SQL surgery on workflow state

Use when the n8n SDK update_workflow fails to apply changes (especially to Code node `jsCode`, Google Sheets `schema`, or credential bindings). The workflow lives in `workflow_entity.nodes` (json) and `workflow_entity.connections` (json).

Canonical pattern — dump, mutate in Python, push back with dollar-quoted SQL:
```bash
# dump
docker exec n8n-postgres-1 psql -U n8n_xeos -d n8n -t -c \
  "SELECT nodes::text FROM workflow_entity WHERE id='WORKFLOW_ID';" > /tmp/nodes.json

# mutate with python (read JSON → modify → write back)
python3 -c "..."

# push back — use dollar-quoted strings to sidestep escaping
python3 -c "
with open('/tmp/nodes.json') as f: c = f.read()
sql = f\"UPDATE workflow_entity SET nodes = \\\$nodes\\\${c}\\\$nodes\\\$::json WHERE id='WORKFLOW_ID';\"
open('/tmp/u.sql','w').write(sql)
"
docker cp /tmp/u.sql n8n-postgres-1:/tmp/u.sql
docker exec n8n-postgres-1 psql -U n8n_xeos -d n8n -f /tmp/u.sql
```

See `assets/workflow-surgery-template.py` for a reusable template that handles dump-mutate-push in one script.

**MCP availability caveat:** if `mcp__n8n-live__get_workflow_details` returns "Workflow is not available in MCP", set `settings.availableInMCP = true` in the DB:
```sql
UPDATE workflow_entity
SET settings = settings::jsonb || '{"availableInMCP":true}'::jsonb
WHERE id='WORKFLOW_ID';
```

## Code node sandbox — what actually works

Probe once, remember forever. In n8n 2.15 Code node (confirmed empirically):

| Construct | Available? | Notes |
|---|---|---|
| `fetch` | ❌ | Not in globalThis. Throws `fetch is not defined`. |
| `$helpers` | ❌ | Doesn't exist. |
| `$http`, `$request` | ❌ | Gone in recent versions. |
| `this.helpers.httpRequest` | ✅ | The only HTTP helper. Axios-backed. |
| `require(...)` | ✅ | Can import npm modules that ship with n8n |
| `Promise.all`, `setTimeout`, `Buffer` | ✅ | Standard Node globals |
| `$input.all()`, `$json`, `$('NodeName').all()` | ✅ | Input data + upstream refs |
| `$input.pairedItem` | ✅ | For joining per-item iterations — see below |

**HTTP in Code node:**
```javascript
const helpers = this.helpers;  // Bind once for reuse
const response = await helpers.httpRequest({
  method: 'POST',
  url: 'https://api.example.com/v1/thing',
  headers: { 'x-api-key': apiKey, 'Content-Type': 'application/json' },
  body: { payload: 1 },
  json: true  // JSON-encode body + parse response
});
```

**Task-runner timeout:** default is 60 seconds. Set `N8N_RUNNERS_TASK_TIMEOUT=600` in `docker-compose.*.yml` for multi-minute polling loops. Even with that raised, never put minute-long waits inside a Code node — use the Wait-node pattern instead.

See `references/code-node-sandbox.md` for the full probe script and more details.

## Long-operation architecture (Submit → Wait → Poll)

Generative APIs (Veo3, ElevenLabs video, Creatomate, JSON2Video) take minutes. Don't put the whole lifecycle in a single Code node — the sandbox will kill it.

```
Code: Submit    — fast POSTs, return operation IDs
  ↓
Wait             — persisted to DB, survives across n8n restarts, zero CPU cost
  ↓
Code: Poll       — short internal loop (maxAttempts × intervalMs within task timeout)
```

Design guideline: **the Wait node should cover ~70% of expected latency**. If Veo3 averages 3 minutes, Wait 180-240s; Poll then handles the last minute of variance. Poll should be resilient: every call returns `{ok, reason, detail}` so the aggregator can drop failed scenes but continue with survivors.

## Per-item iteration (fan-out → aggregate)

For N-scene pipelines (multi-clip video, batch enrichment, parallel API calls):

```
Code: Emit N items       (runOnceForAllItems, returns array)
  ↓                      [each subsequent node fires N times]
HTTP: per-item call
  ↓
Drive/S3: per-item upload
  ↓
Code: Aggregate          (runOnceForAllItems, reads $input.all())
```

**Joining data after iteration:** downstream nodes (especially `googleDrive.upload`) **overwrite `$json` with their own output fields**, losing `message`/`sceneName`/etc. from the original emit. To recover, the aggregator reads from both the previous node and the original emit node via `pairedItem.item`:

```javascript
const poll = $('Upstream: Emit N Items').all();
const driveItems = $input.all();
const joined = driveItems.map((d, i) => {
  const pi = d.pairedItem && typeof d.pairedItem === 'object' ? d.pairedItem.item : i;
  const meta = (poll[pi] && poll[pi].json) || {};
  const drive = d.json || {};
  return { ...meta, driveUrl: drive.webContentLink, driveFileId: drive.id };
});
```

## Resilient polling for generative APIs

Generative APIs fail in three distinct ways; handle each explicitly. Never let one bad scene abort a 3-scene pipeline.

```javascript
async function poll(opName, maxAttempts=36, intervalMs=15000) {
  for (let i=0; i<maxAttempts; i++) {
    const j = await helpers.httpRequest({ method: 'GET', url: `${base}/${opName}`, headers, json: true });
    if (j.done) {
      if (j.error) return { ok: false, reason: 'internal_error', detail: `${j.error.code} ${j.error.message}` };
      const uri = j.response?.generateVideoResponse?.generatedSamples?.[0]?.video?.uri;
      if (uri) return { ok: true, url: uri };
      if (j.response?.generateVideoResponse?.raiMediaFilteredReasons?.[0]) {
        return { ok: false, reason: 'rai_filter', detail: j.response.generateVideoResponse.raiMediaFilteredReasons[0] };
      }
      return { ok: false, reason: 'unknown', detail: JSON.stringify(j).slice(0,300) };
    }
    if (i < maxAttempts - 1) await new Promise(r => setTimeout(r, intervalMs));
  }
  return { ok: false, reason: 'timeout', detail: opName };
}

// Drop failed items; proceed with survivors. Only throw if ALL failed.
const results = await Promise.all(ops.map(poll));
const good = results.filter(r => r.ok);
if (good.length === 0) throw new Error(`All failed: ${JSON.stringify(results)}`);
```

## Rate-limit handling

Sequential submits with 2-3s spacing avoid per-second limits. Exponential backoff with 45s+ base delay handles 429s. Parallel `Promise.all` for submission is tempting but brittle — generative APIs rate-limit hard.

```javascript
async function submitOne(scene, maxRetries=4) {
  for (let attempt=0; attempt<maxRetries; attempt++) {
    try {
      const j = await helpers.httpRequest({...});
      if (j.name) return j.name;
    } catch (e) {
      const msg = e.message || '';
      const is429 = /429/.test(msg) || /RESOURCE_EXHAUSTED/i.test(msg);
      const backoff = is429 ? 45000 * Math.pow(1.5, attempt) : 4000;
      if (attempt < maxRetries - 1) await new Promise(r => setTimeout(r, backoff));
    }
  }
  throw new Error(`Failed after ${maxRetries} retries`);
}

const ops = [];
for (let i=0; i<scenes.length; i++) {
  ops.push(await submitOne(scenes[i]));
  if (i < scenes.length - 1) await new Promise(r => setTimeout(r, 3000));  // spacing
}
```

## Google Sheets gotchas

1. **Schema drift:** the `appendOrUpdate` op maps columns by position, not name. If your node was created when the sheet had 4 columns but the sheet now has 8, you get `Column names were updated after the node's setup`. Always include the **full current schema** in every Sheets node's `parameters.columns.schema`. When you add a column to the sheet, patch every node that writes to it.

2. **Empty-state flow:** `alwaysOutputData: true` on a read node makes it emit an empty item when no rows match. Without it, downstream nodes silently skip on first-time records.

3. **Dedup pattern:** check a **completion marker** column (e.g., `URL VIDEO FINAL`), not an early-pipeline column. Partial runs populate early columns but leave the completion marker empty — so retries can reprocess.

## Idempotency + dedup (for paid-API pipelines)

Every pipeline that calls paid/stateful APIs (Veo3 at ~$0.50/clip, Creatomate quota) must dedupe at the start:

```
Trigger → Config → Read State (Sheets/Notion, alwaysOutputData=true)
        → Resolve Dedup (Code, runOnceForAllItems)
        → IF isDuplicate?
           ├─ TRUE  → [notify only; skip upload] → Merge
           └─ FALSE → [upload image, do work]   → Merge
        → Merge → shared downstream (Vision, Gen, Publish…)
```

Both branches must converge at a `Merge` node if downstream shares code — otherwise TRUE branch terminates and re-runs do nothing. Downstream code references shared fields from the dedup resolver, not from branch-specific nodes that may or may not have executed (use ternary based on `action` flag: `action === 'SKIP' ? existingUrl : newUrl`).

## Integration specifics

Each external service has quirks significant enough to warrant a reference card:

| Service | Reference |
|---|---|
| Gemini Veo 3.0 / 3.1 | `references/veo-integration.md` |
| JSON2Video | `references/json2video-integration.md` |
| Code node sandbox capabilities | `references/code-node-sandbox.md` |
| SQL surgery workflow | `references/sql-surgery.md` |

**Telegram sendVideo quirk (cross-cutting):** the `file` URL is fetched server-side by Telegram. It cannot fetch Google Drive `webContentLink` (auth-wall), AWS S3 presigned URLs (expire too fast if Telegram delays), or other URLs that require auth. If the URL may be restricted, download to binary via n8n HTTP node and use `binaryData: true` — or just switch to `sendMessage` with the URL as text.

## Debugging checklist

When an exec fails, in order:

1. **Pull the last node executed and its error** — `docker exec n8n-postgres-1 psql -U n8n_xeos -d n8n -t -c "SELECT data::text FROM execution_data WHERE \"executionId\"=<N>;"` returns a flattened reference array; grep for `Error` / `error_code` / specific error strings.
2. **Check the node's full input** — especially after iterations; downstream nodes often lose fields. Look for undefined or empty strings in request bodies.
3. **If Code node** — check for `fetch is not defined`, `$helpers is not defined`, or silent timeout (output in <100ms when loop should have taken minutes = task-runner killed).
4. **If 429** — check provider quota (not just rate). `RESOURCE_EXHAUSTED` typically means daily cap, not per-minute. Switch to a different model variant (veo-3.0 vs veo-3.1-lite — they have separate quotas) or wait for reset.
5. **If "Column names were updated"** — full schema in every Sheets node.
6. **If `$env.X` is `undefined`** — missing `- X=${X}` in docker-compose, or `N8N_BLOCK_ENV_ACCESS_IN_NODE` not set to `false`, or container needs restart.
7. **If credentials missing** — verify all 4 locations are in sync and n8n credential ID matches what's referenced in the node.

## Cost & quota awareness

When designing pipelines, note the paid steps and their failure modes:

- **Gemini Veo 3.0**: ~$0.50/clip, hard daily quota, 8s cap, 2-5 min generation, 10% RAI-filter rate on innocuous prompts (audio gen is the common trigger)
- **Gemini Veo 3.1 / 3.1-lite**: separate quota from 3.0 — swap via `GEMINI_VEO_MODEL` env var when one exhausts
- **Veo-generated files**: ~2h TTL on Google's CDN; download to durable storage (Drive/S3) immediately if you need them later
- **JSON2Video**: free tier has ~couple seconds of render time total; paid plans unlock. Request body is rejected with `Property 'text' is required in movie/scenes[N]/elements[K]` if `voice` element lacks text. Cannot fetch auth-walled URLs for `video.src`
- **Creatomate**: monthly render quota; response is `[{...}]` array (not object) — downstream references must use `.json[0].id` or accept both; template var substitution via `modifications: { "Key.name": "value" }`

Always budget for 1-2 full E2E test runs of any pipeline you build — that's typically the cost of catching the gotchas above.
