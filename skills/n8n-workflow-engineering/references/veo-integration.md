# Gemini Veo integration reference

Covers `veo-3.0-generate-001` and `veo-3.1-generate-preview` / `veo-3.1-lite-generate-preview`. API surface is the Gemini `predictLongRunning` endpoint.

## Models — choose deliberately

| Model | Generation time | Quota behavior | Quality | Notes |
|---|---|---|---|---|
| `veo-3.0-generate-001` | ~90s-2min | Hard daily cap on free tier | Highest | Best for cinematic quality |
| `veo-3.1-generate-preview` | ~2-3min | Separate quota from 3.0 | Very good | Preview model, may change |
| `veo-3.1-lite-generate-preview` | ~2-5min | Separate quota from 3.0/3.1 | Good | Fallback when 3.0 exhausted; still generates audio |

All of them cap at **8 seconds per clip** (`durationSeconds` max 8; min 4). All generate audio natively (not disableable) — which is the most common cause of RAI filter trips even on innocuous visual prompts.

## Submit — predictLongRunning

```bash
curl -s "https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:predictLongRunning" \
  -H "x-goog-api-key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "instances": [{"prompt": "cinematic close-up of a single apple on a marble table"}],
    "parameters": {
      "aspectRatio": "9:16",
      "durationSeconds": 8,
      "personGeneration": "allow_all"
    }
  }'
```

Returns `{"name": "models/${MODEL}/operations/${OP_ID}"}`.

**Parameters:**
- `aspectRatio` — `"16:9"` (landscape, YouTube), `"9:16"` (Reels/Shorts/TikTok), `"1:1"` (square feed). Pick based on distribution channel; parameterize via env (`VEO_ASPECT_RATIO`).
- `durationSeconds` — 4-8 inclusive
- `personGeneration` — `"allow_all"` (most permissive), `"allow_adult"`, `"dont_allow"`. `allow_all` is still subject to RAI filters.
- `sampleCount` — default 1; can request up to 3 samples (costs multiples)

**Prompt conventions:**
- Describe visuals only (setting, subject, camera motion, lighting, mood)
- Avoid anything about text, logos, captions, titles — Veo will try to render them (looks bad) and can trip RAI
- Append a suffix like: *"No on-screen text, captions, subtitles, titles, watermarks, logos, or typography."* Helps but not perfect.
- Keep prompts 30-80 words. Longer → more RAI sensitivity.

## Poll — predictLongRunning status

```bash
curl -s "https://generativelanguage.googleapis.com/v1beta/${OP_NAME}" \
  -H "x-goog-api-key: $KEY"
```

Returns incrementally:
```json
{"name": "...", "done": false}                          // still generating
{"name": "...", "done": true, "response": {...}}        // done
{"name": "...", "done": true, "error": {...}}           // failed
```

## Three distinct terminal states

```json
// 1. Success
{
  "done": true,
  "response": {
    "@type": "...",
    "generateVideoResponse": {
      "generatedSamples": [
        {"video": {"uri": "https://generativelanguage.googleapis.com/v1beta/files/XXX:download?alt=media"}}
      ]
    }
  }
}

// 2. RAI filter (AUDIO gen most commonly triggers, even for safe visual prompts)
{
  "done": true,
  "response": {
    "@type": "...",
    "generateVideoResponse": {
      "raiMediaFilteredCount": 1,
      "raiMediaFilteredReasons": [
        "We encountered an issue with the audio for your prompt..."
      ]
    }
  }
}

// 3. Internal error
{
  "done": true,
  "error": {
    "code": 13,
    "message": "Video generation failed due to an internal server issue. Please try again..."
  }
}
```

Also possible: **timeout** — `done` never becomes `true` in reasonable time (>8 minutes for 3.1-lite under load). Treat as a fourth failure mode.

Always handle all four in the polling code. Don't let one failure abort a multi-scene pipeline.

## URL lifetime + download

Generated video URIs look like `https://generativelanguage.googleapis.com/v1beta/files/XXX:download?alt=media` and require the API key. Two auth options:

```bash
# URL param (works for external fetchers like JSON2Video, Creatomate)
curl -L "${URI}&key=${KEY}"

# Header (cleaner for our own downloads)
curl -L -H "x-goog-api-key: ${KEY}" "${URI}"
```

**Critical: URIs expire in ~2 hours.** Download and store durably immediately after generation — don't try to re-reference across sessions.

## Rate limits & quotas

- **Per-minute rate limit** (~5-10/min depending on tier) — causes transient 429 with "RESOURCE_EXHAUSTED"
- **Daily quota** (tier-dependent) — 429 with "You exceeded your current quota"
- Same error code for both; they look identical but recover differently

Retry strategy:
- Treat 429 as retryable with **exponential backoff (base 45s)** — per-minute limit will clear in <60s
- If multiple retries still 429, it's a daily quota — switch to a different model variant (3.0 ↔ 3.1-lite), or wait for reset (~24h)

Submission pattern:
- **Sequential** submits with 2-3s spacing between scenes avoid per-second throttling
- **Polling** can be parallel via `Promise.all` — read requests are much cheaper

## Cost (approximate)

- Veo 3.0: $0.50 per 8s clip (billed on generation, not on poll)
- Veo 3.1 preview: similar
- Veo 3.1 lite: cheaper (~$0.25-0.35/clip, haven't been officially priced)

**You're not charged for RAI-filtered attempts** (confirmed by the filter message).

## Full n8n Code node implementation (battle-tested)

```javascript
const helpers = this.helpers;
const cfg = $('Config: Workflow Parameters').item.json;
const apiKey = cfg.GEMINI_API_KEY;
const model = cfg.GEMINI_VEO_MODEL;  // e.g., 'veo-3.1-lite-generate-preview'
const aspectRatio = cfg.VEO_ASPECT_RATIO || '9:16';
const personGeneration = cfg.VEO_PERSON_GENERATION || 'allow_all';

const NO_TEXT = 'Important: do NOT render any on-screen text, captions, subtitles, titles, watermarks, logos, or typography in the video frame. Pure cinematic UGC visual footage only.';
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

async function veoSubmit(scene, maxRetries=4) {
  const d = Math.min(Math.max(Number(scene.duration_max_seconds) || 8, 4), 8);
  const body = {
    instances: [{ prompt: `${scene.prompt}. ${NO_TEXT}` }],
    parameters: { aspectRatio, durationSeconds: d, personGeneration }
  };
  let lastErr;
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      const j = await helpers.httpRequest({
        method: 'POST',
        url: `https://generativelanguage.googleapis.com/v1beta/models/${model}:predictLongRunning`,
        headers: { 'x-goog-api-key': apiKey, 'Content-Type': 'application/json' },
        body, json: true
      });
      if (j && j.name) return j.name;
      lastErr = new Error(`no name: ${JSON.stringify(j).slice(0,200)}`);
    } catch (e) {
      lastErr = e;
      const is429 = /429/.test(e.message || '') || /RESOURCE_EXHAUSTED/i.test(e.message || '');
      const backoff = is429 ? 45000 * Math.pow(1.5, attempt) : 4000;
      if (attempt < maxRetries - 1) await sleep(backoff);
    }
  }
  throw new Error(`Veo submit failed (${scene.name}): ${lastErr.message}`);
}

async function veoPoll(opName, maxAttempts=36, intervalMs=15000) {
  for (let i=0; i<maxAttempts; i++) {
    const j = await helpers.httpRequest({
      method: 'GET',
      url: `https://generativelanguage.googleapis.com/v1beta/${opName}`,
      headers: { 'x-goog-api-key': apiKey },
      json: true
    });
    if (j.done) {
      if (j.error) return { ok: false, reason: 'internal_error', detail: `${j.error.code} ${j.error.message}`.slice(0,300) };
      const resp = j.response?.generateVideoResponse || {};
      const uri = resp.generatedSamples?.[0]?.video?.uri;
      if (uri) return { ok: true, url: uri };
      if (resp.raiMediaFilteredReasons?.[0]) return { ok: false, reason: 'rai_filter', detail: resp.raiMediaFilteredReasons[0] };
      return { ok: false, reason: 'unknown', detail: JSON.stringify(j).slice(0,300) };
    }
    if (i < maxAttempts - 1) await sleep(intervalMs);
  }
  return { ok: false, reason: 'timeout', detail: opName };
}

// Sequential submit with spacing, parallel poll
const ops = [];
for (let i = 0; i < scenes.length; i++) {
  ops.push(await veoSubmit(scenes[i]));
  if (i < scenes.length - 1) await sleep(3000);
}

const results = await Promise.all(ops.map(veoPoll));
```

## Common failures

| Error / symptom | Cause | Fix |
|---|---|---|
| `"You exceeded your current quota"` (429) | Daily quota | Switch `GEMINI_VEO_MODEL` to another variant; or wait 24h |
| `"Request failed with status code 429"` intermittent | Per-minute rate limit | Sequential submission + exponential backoff |
| `raiMediaFilteredReasons: [...]` | Audio gen tripped safety | Rephrase prompt; add "serene", "silent" keywords; or skip scene |
| `error.code: 13, "internal server issue"` | Google-side flake | Drop scene, retry entire operation later |
| Video URI returns 404 on download | >2h TTL expired | Regenerate; download to durable storage faster |
| Generated video has text overlays | Prompt referenced text | Add explicit no-text directive; keep regenerating |
