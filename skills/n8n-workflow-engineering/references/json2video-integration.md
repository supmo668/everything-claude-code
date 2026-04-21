# JSON2Video integration reference

JSON2Video renders multi-scene videos (stitching, voiceovers, subtitles, overlays) via a JSON declarative API. Drop-in replacement for Creatomate for compositing needs. Free tier is extremely limited; paid plans unlock production usage.

## Authentication — two patterns

**Pattern A — env-based header injection (preferred for new workflows):**
```yaml
sendHeaders: true
headerParameters:
  parameters:
    - name: x-api-key
      value: "={{ $('Config: Workflow Parameters').item.json.J2V_API_KEY }}"
```

**Pattern B — n8n httpCustomAuth credential (matches reference workflow):**
```bash
docker exec n8n n8n import:credentials --input=/tmp/j2v.json
# where j2v.json contains:
# [{"id":"j2v-api-key","name":"JSON2Video API","type":"httpCustomAuth",
#   "data":{"json":"{\"headers\":{\"x-api-key\":\"...\"}}"}}]
```

Either works. Pattern A is simpler (one fewer artifact); Pattern B is cleaner if you're using the reference workflow template.

## Endpoints

```
POST https://api.json2video.com/v2/movies        # start a render
GET  https://api.json2video.com/v2/movies?id=X   # check status
```

**Submit response:**
```json
{ "success": true, "project": "abc123", "timestamp": "..." }
```

**Status response when rendering:**
```json
{ "success": true, "movie": { "status": "processing", ... } }
```

**Status response when done:**
```json
{
  "success": true,
  "movie": {
    "success": true,
    "status": "done",
    "url": "https://json2video-cdn1.s3.amazonaws.com/clients/.../renders/X.mp4",
    "ass": "https://.../X.ass",
    "rendering_time": 17,
    ...
  }
}
```

**Status response when failed:**
```json
{
  "success": true,
  "movie": {
    "success": false,
    "status": "error",
    "message": "Scene #2, element #1: Failed to download Google Drive URL: ...",
    "url": null,
    ...
  }
}
```

Note the dual `success`: the outer `success` is whether the API call worked; `movie.success` is whether the render succeeded. Always check both.

## Payload shape

Minimum viable multi-scene payload:
```json
{
  "resolution": "custom",
  "width": 1080,
  "height": 1920,
  "quality": "high",
  "scenes": [
    {
      "id": "scene_1",
      "comment": "Scene 1 label for logs",
      "elements": [
        { "type": "video", "src": "https://...", "muted": true },
        { "type": "voice", "text": "narration line", "voice": "en-US-AriaNeural" }
      ]
    },
    {
      "id": "scene_2",
      "elements": [
        { "type": "video", "src": "https://...", "muted": true },
        { "type": "voice", "text": "second narration", "voice": "en-US-AriaNeural" }
      ]
    }
  ],
  "elements": [
    {
      "type": "subtitles",
      "settings": {
        "style": "classic-progressive",
        "font-family": "Oswald",
        "font-size": 70,
        "word-color": "#FCF5C9",
        "shadow-color": "#260B1B",
        "line-color": "#F1E7F4",
        "shadow-offset": 2,
        "box-color": "#260B1B"
      },
      "language": "en"
    },
    {
      "type": "text",
      "text": "Title overlay",
      "start": 0,
      "duration": 3,
      "settings": { "font-size": 90, "color": "#FCF5C9", "text-align": "center", "vertical-align": "top" }
    },
    {
      "type": "text",
      "text": "BrandTag",
      "settings": { "font-size": 42, "text-align": "right", "vertical-align": "bottom" }
    }
  ]
}
```

**Scenes vs global elements:**
- `scenes[]` — each scene has its own elements, plays sequentially
- Root `elements[]` — span the whole video (subtitles, persistent title, brand tag)

**Resolutions:**
- Preset: `"hd"` (1920x1080), `"full-hd"`, `"4k"`, etc.
- `"custom"` with explicit `width` + `height` — use for 9:16 (1080x1920) Reels

## Element types that matter

| Type | Purpose | Required fields |
|---|---|---|
| `video` | Play a video clip | `src` (public URL) |
| `voice` | TTS voiceover | `text`, `voice` (Azure Neural code) |
| `audio` | Background music / external audio | `src` |
| `text` | On-screen text overlay | `text` |
| `subtitles` | Auto-captions from voice elements | — (global only) |
| `image` | Static image overlay | `src` |

**Voice element requires `text`.** The server returns `Property 'text' is required in movie/scenes[N]/elements[K]` if you forget it or pass empty. Common cause: downstream aggregator lost the `message` field from upstream because the Drive Upload node overwrote `$json`. See the pairedItem-join pattern in SKILL.md.

## Voice options (en-US-AriaNeural etc.)

Uses Azure Cognitive Services Neural voices. Common codes:
- `en-US-AriaNeural` — female, friendly, default American
- `en-US-GuyNeural` — male American
- `en-US-JennyNeural` — female, conversational
- `en-GB-SoniaNeural` — female British
- `en-AU-NatashaNeural` — female Australian

Full list at Microsoft's Azure voices page; cross-reference with JSON2Video docs since not all are enabled.

## Critical gotcha: src must be publicly fetchable

JSON2Video's rendering backend fetches `video.src` URLs server-side. It **cannot** fetch:

- Google Drive `webContentLink` / `webViewLink` — auth-walled even when "anyone with link"; Google redirects through a virus-scan page for files >25MB
- AWS S3 pre-signed URLs that require specific region headers
- Any URL returning HTML instead of binary
- URLs with auth headers (the backend only supports URL-embedded auth)

**What works:**
- Public CDN URLs
- Google Veo URIs with `&key=API_KEY` appended: `https://generativelanguage.googleapis.com/v1beta/files/XXX:download?alt=media&key=...`
- Backblaze B2 public URLs
- Cloudinary public URLs

**If you need Drive URLs to be fetchable externally:** add a Drive "share" operation to set `role: reader, type: anyone`. Even then, large-file virus-scan redirects may bite. Safer: don't feed Drive URLs to external services; use them only for our own audit trail.

## Free tier limits

Couple seconds of render time. One real multi-scene video (~16s output, ~11-17s render time) exhausts it. Paid plans unlock this.

The API returns `"remaining_quota": { "time": N }` in status responses; if this drops to 0-5, expect the next render to error with "You exceeded the quota of time in your plan".

## Full n8n HTTP node config

```javascript
// Render submit
{
  method: 'POST',
  url: 'https://api.json2video.com/v2/movies',
  sendHeaders: true,
  headerParameters: {
    parameters: [
      { name: 'x-api-key', value: "={{ $('Config: Workflow Parameters').item.json.J2V_API_KEY }}" }
    ]
  },
  sendBody: true,
  specifyBody: 'json',
  jsonBody: '={{ JSON.stringify($json.j2vBody) }}'
}

// Status poll (after Wait)
{
  method: 'GET',
  url: "=https://api.json2video.com/v2/movies?id={{ $('JSON2Video: Render').first().json.project }}",
  sendHeaders: true,
  headerParameters: {
    parameters: [
      { name: 'x-api-key', value: "={{ $('Config: Workflow Parameters').item.json.J2V_API_KEY }}" }
    ]
  }
}
```

Chain it with an n8n `Wait` node set to 60s. Typical render is 11-17s, so one poll suffices for simple pipelines. For long videos or under load, wrap the status check in a loop (Wait → GET → IF done → back to Wait).

## Pick-Final-Output pattern (fallback to Drive)

When JSON2Video fails (quota, bad URL, payload bug), don't abort the workflow. Choose between composite and per-scene fallback:

```javascript
const build = $('Build J2V Payload').item.json;
const status = $json || {};
const movie = status.movie || {};
const j2vOk = movie.success === true && !!movie.url;
const driveUrls = build.driveUrls || [];

const finalUrl = j2vOk ? movie.url : (driveUrls[0] || '');
const kind = j2vOk ? 'json2video_composite' : (driveUrls.length ? 'drive_scene_fallback' : 'none');
const note = j2vOk
  ? 'Composite rendered by JSON2Video.'
  : (movie.message ? `JSON2Video unavailable (${movie.message}). Using Drive fallback.` : 'No output.');

return [{ json: { finalUrl, kind, note, allDriveUrls: driveUrls, j2vStatus: movie.status, j2vMessage: movie.message } }];
```

Downstream nodes reference `$('Pick Final Output').item.json.finalUrl`. They don't need to know whether J2V or the Drive fallback produced it.

## Reference workflow

Template workflow `7lpvpzSxwkEJxAzM` ("Automatically generate burn-in video captions with json2video") ships with n8n's template library. Useful for:
- Canonical header/auth setup
- Subtitles-only simple rendering (no voice)
- Confirming payload shape when your custom build fails validation

Diff your failing payload against that one when stuck.
