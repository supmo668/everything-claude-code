# n8n Code Node Sandbox — empirical reference

The n8n 2.x Code node runs JavaScript in a task-runner subprocess with a specific VM context. What works and what doesn't is not fully documented — this reference captures what was verified by running a probe on n8n 2.15.

## Probe script (paste into any Code node to reintrospect)

```javascript
const probe = {
  hasFetch: typeof fetch !== 'undefined',
  hasHelpers: typeof $helpers !== 'undefined',
  hasThisHelpers: typeof this !== 'undefined' && typeof this.helpers !== 'undefined',
  hasHttp: typeof $http !== 'undefined',
  hasRequest: typeof $request !== 'undefined',
  globals: Object.keys(globalThis).filter(k => !k.startsWith('__')).slice(0, 30),
};
try { probe.thisKeys = Object.keys(this || {}); } catch(e) { probe.thisKeys = 'err:' + e.message; }
return [{ json: probe }];
```

Run it, inspect the output item in the n8n UI. This is cheap and gives a definitive answer for the current version.

## Confirmed availability (n8n 2.15)

**Available globals (via globalThis):**
- `module`, `global`, `require`, `console`
- `Buffer`, `setTimeout`, `setInterval`, `setImmediate`, clearing variants
- `btoa`, `atob`, `TextDecoder`, `TextEncoder`, streams variants
- `FormData`
- `$`, `$input`, `$binary`, `$data`, `$env`, `$evaluateExpression`, `$item`, `$items`
- `$fromAI` / `$fromai` / `$fromAi`

**Available via `this` (but NOT as globals):**
- `this.helpers` — includes `httpRequest()` (Axios-backed), and some other helpers
- `this.$getWorkflowStaticData` — persistent KV store scoped to workflow
- `$json`, `$node`, `$self`, `$parameter`, `$prevNode`, `$runIndex`, `$mode`, `$workflow`, `$itemIndex`
- `$now`, `$today`, `$jmesPath`, `DateTime`, `Interval`, `Duration`
- `$execution`, `$vars`, `$secrets`, `$executionId`, `$resumeWebhookUrl`
- `$getPairedItem`, `$position`, `$thisItem`, `$thisItemIndex`, `$thisRunIndex`, `$nodeVersion`, `$nodeId`

**Explicitly NOT available:**
- `fetch` — throws `fetch is not defined`. Use `this.helpers.httpRequest`.
- `$helpers` — throws `$helpers is not defined`. It's `this.helpers`, not a global.
- `$http`, `$request` — older names, not in 2.x.

## HTTP via `this.helpers.httpRequest`

Supports everything axios does. Most useful options:

```javascript
const helpers = this.helpers;

// JSON request/response
const j = await helpers.httpRequest({
  method: 'POST',
  url: 'https://api.example.com/v1/thing',
  headers: { 'Authorization': `Bearer ${token}` },
  body: { name: 'test' },
  json: true   // encode body as JSON + parse response as JSON
});

// Binary download
const bin = await helpers.httpRequest({
  method: 'GET',
  url: 'https://example.com/video.mp4',
  encoding: null,    // return Buffer
  returnFullResponse: false
});

// Form-encoded
const form = await helpers.httpRequest({
  method: 'POST',
  url: 'https://api.example.com/v1/form',
  form: { field: 'value' }
});
```

**Error handling:** helpers.httpRequest throws on non-2xx responses. Wrap in try/catch and inspect `e.message`, `e.statusCode`, `e.response`. 4xx/5xx messages typically contain the HTTP code, useful for discriminating 429 vs 400 vs 500.

## Task-runner timeouts

Default **60 seconds**. For long polling loops, set in `docker-compose.*.yml`:

```yaml
services:
  n8n:
    environment:
      - N8N_RUNNERS_TASK_TIMEOUT=600
```

Symptom of hitting this limit: Code node reports `executionTime: <100ms` or similar short duration, output is empty or truncated, the workflow proceeds as if the Code returned immediately. Not a thrown error — silent kill.

Even with timeout raised, never design a Code node to wait for many minutes synchronously. Use the **Submit → Wait → Poll** pattern where the long wait lives in an n8n `Wait` node.

## Patterns by runMode

**`runOnceForAllItems`** — the node runs ONE TIME with `$input.all()` giving the full array. Return `[{ json: ... }, { json: ... }]` to emit N items. Use for aggregation or fan-out.

**`runOnceForEachItem`** — the node runs ONCE PER INPUT ITEM. `$json` is the current item. Return `{ json: ... }` (single object, no array wrapper). Use for per-item transforms.

**When iterating downstream from a `runOnceForAllItems` that emits N items:** each subsequent node fires N times. To rejoin outputs afterward, aggregate with a `runOnceForAllItems` Code node using `$input.all()`.

## Accessing prior nodes

```javascript
// All items from a specific upstream node
const items = $('NodeName').all();

// First item from upstream node (when the upstream emitted one item only)
const first = $('NodeName').first().json;

// Current item's upstream ref (position-paired)
const current = $('NodeName').item.json;
```

## Persistent state (careful)

`this.$getWorkflowStaticData('global')` returns a mutable object that persists across executions of the same workflow. Useful for counters, accumulators, simple KV. Don't store secrets there (accessible via the n8n UI).

```javascript
const state = this.$getWorkflowStaticData('global');
state.counter = (state.counter || 0) + 1;
```

## require() caveats

`require()` works but the module must already be installed in the n8n container's `node_modules`. You can `require('crypto')`, `require('path')`, `require('fs')` (node built-ins) reliably. npm modules that n8n itself uses (axios, lodash, etc.) are hit-or-miss — version may shift under you across upgrades.

Safer: if you need a specific library, wrap its functionality in an HTTP service and call it via `helpers.httpRequest`.

## Common errors & fixes

| Symptom | Cause | Fix |
|---|---|---|
| `fetch is not defined` | Using browser-style fetch | Use `this.helpers.httpRequest` |
| `$helpers is not defined` | Wrong variable name | `const helpers = this.helpers` |
| Code node returns instantly with empty output | Task-runner timeout hit | Raise `N8N_RUNNERS_TASK_TIMEOUT` + use Wait-node pattern |
| `Cannot read property 'json' of undefined` | Accessing `$('NodeX').item` when NodeX didn't execute (IF branch, etc.) | Guard with `$('NodeX').item?.json` or reference from a node that always runs |
| JSON output silently becomes string | Forgot `.json` wrapper in return | `return [{ json: {...} }]`, not `return [{...}]` |
| Downstream sees only first item | Returning object instead of array | Use `return items` (array), not `return items[0]` |
