---
name: outreach-brief
description: Generate a research-backed pre-call brief AND personalized warm outreach email for a sales prospect. Extends call-brief with signal-driven narrative selection and HTML email generation. Input a contact name, title, company — outputs a brief + ready-to-send personalized warm email. Optionally accepts a base email template and personalization instructions.
origin: project
metadata:
  filePattern: ["**/dealflow/briefs/**", "**/email-templates/**/warm/**", "**/call-scripts*", "**/signal-flowchart*"]
  bashPattern: []
---

# Outreach Brief Generator

Synthesize a complete outreach package for a warm lead: research-backed pre-call brief + personalized warm intro email. Combines the call-brief workflow with signal-driven narrative selection and HTML email generation.

## When to Activate

- User says `/outreach-brief [Contact Name], [Title] at [Company]`
- User asks to "generate an outreach package" or "prep outreach for [person]"
- User asks to "create a warm email and brief for [person]"

## Input Format

```
/outreach-brief [Contact Name], [Title] at [Company Name]
```

**Optional arguments:**
- `--template [path]` — Base email template to personalize (default: `H&W DTC - Protocol Retention/warm/warm-lead-personal.html`)
- `--instructions "[text]"` — Custom personalization instructions (e.g., "reference their recent product launch", "use FSD narrative", "mention mutual connection via [name]")
- `--narrative [companion|intelligence|moat|compliance|platform]` — Force a specific narrative instead of auto-detecting
- `--segment [dtc|fsd]` — Force DTC or FSD segment (affects meeting link and deck)

Examples:
- `/outreach-brief Nikul Panchal, Chief Pharmacy Officer at Wellgistics Health`
- `/outreach-brief Shane Heath, Founder at MUD\WTR --narrative companion`
- `/outreach-brief Larry Kemp, Product Owner at New U Life --template warm/warm-1-intro.html --instructions "reference SomaDerm protocol complexity and his Unicity background"`
- `/outreach-brief VP Quality at RXBAR --segment fsd --narrative compliance`

## Workflow

### Step 1: Generate Call Brief (inherits from call-brief)

Execute the FULL call-brief workflow (Steps 1-4):
1. Research the company (web search + Apollo enrichment)
2. Determine narrative & tier using signal flowchart logic
3. Generate the brief with all 11 sections
4. Save to `sales_gtm/docs/dealflow/briefs/{company-kebab-case}.md`

**This step is identical to `/call-brief`.** Do not duplicate the logic — follow the call-brief SKILL.md workflow exactly.

### Step 2: Apply Signal Flowchart Logic

After the brief is generated, apply the narrative selection logic from `sales_gtm/docs/dealflow/signal-flowchart.md` Section 3:

```
Prospect → Tier Detection → Pain Detection → Narrative Selection
```

**Narrative selection rules:**

| Tier | Default Narrative | Override Conditions |
|------|------------------|-------------------|
| Tier 1 (DTC Founder, 1-50 emp) | Companion | Intelligence if data-focused; Moat if differentiation pain |
| Tier 2 (Scaling Brand, 51-500 emp) | Intelligence | Companion if engagement pain; Moat if competitive anxiety |
| Tier 3 (Food Safety, 10-500 emp) | Compliance Shield | Always compliance unless explicitly platform |
| Platform/SaaS | Platform Extension | Always platform |

**If `--narrative` flag is provided, skip auto-detection and use the specified narrative.**

Each narrative drives different email tone and content:

| Narrative | Email Tone | Opening Hook | Core Question | CTA Framing |
|-----------|-----------|-------------|---------------|-------------|
| **Companion** | Warm, founder-to-founder | "Your customers deserve a daily companion" | "What happens after someone buys [product]?" | "Worth 15 minutes to see what this looks like?" |
| **Intelligence** | Metric-driven, VP-level | "You're optimizing the transaction but flying blind on usage" | "Can you tell me what % complete a full cycle?" | "Worth 30 minutes to see your retention data?" |
| **Competitive Moat** | Urgency, differentiation | "95,000 supplement SKUs on Amazon. How does [product] stand out?" | "If a competitor launches AI-guided protocols tomorrow, what's your response?" | "First movers own the protocol layer" |
| **Compliance Shield** | Risk-focused, regulatory | "37 states, 75+ ingredient bills" | "Are you confident every SKU is compliant across every state?" | "See your ingredient risk score — 30 min" |
| **Platform Extension** | Technical, partnership | "Embed an AI companion without building it yourself" | "What would it take your team to build this in-house?" | "Let's scope a whitelabel integration" |

### Step 3: Select or Create Email Template

**If `--template` is provided:**
- Read the specified template file
- Use it as the base HTML structure
- Replace placeholders with researched content

**If no template specified, auto-select based on narrative:**

| Narrative | Default Template | Meeting Link |
|-----------|-----------------|-------------|
| Companion | `warm/warm-1-intro.html` | DTC meeting link |
| Intelligence | `warm/warm-lead-personal.html` | DTC meeting link |
| Competitive Moat | `warm/warm-lead-personal.html` | DTC meeting link |
| Compliance Shield | `warm/warm-lead-personal.html` | FSD meeting link |
| Platform Extension | `warm/warm-lead-personal.html` | DTC meeting link |

**Meeting links (from config.js):**
- DTC: `https://www.reach.syntropyhealth.bio/meetings/welcome-to-syntropy/syntropy-partner-dtc`
- FSD: `https://www.reach.syntropyhealth.bio/meetings/welcome-to-syntropy/syntropy-partner-fsd`

**CRITICAL: Warm emails always link to the meeting page, NOT the intake page.** Warm leads already have context — the goal is to book a call directly.

### Step 4: Generate Personalized Email

Using the selected template as a structural base, generate a personalized HTML email.

**Email files contain a commented header + body-only HTML.** No `<!DOCTYPE>`, `<html>`, `<head>`, `<style>`, or `<title>`. The file starts with a metadata comment block, then `<body>...</body>` for copy-paste.

**Required comment header format** (before `<body>` tag):
```html
<!--
  ╔══════════════════════════════════════════════════════════════╗
  ║  TO: {Contact Name} — {Title}                               ║
  ║  AT: {Company Name}                                          ║
  ║                                                              ║
  ║  SUBJECT A: {Subject line A}                                 ║
  ║  SUBJECT B: {Subject line B}                                 ║
  ║  SUBJECT C: {Subject line C}                                 ║
  ║                                                              ║
  ║  NARRATIVE: {Narrative}  |  PRIORITY: {P0-P3}                ║
  ║  BRIEF: briefs/{company}.md                                  ║
  ║                                                              ║
  ║  ⚠  COPY FROM <body> TAG BELOW — NOT THIS HEADER            ║
  ╚══════════════════════════════════════════════════════════════╝
-->
```

This header is for quick reference when opening the file — subject lines, priority, and brief link are visible at a glance. The same metadata also lives in the `warm/README.md` index.

Email body content:

1. **Preheader** — Product-specific hook (hidden div, ~100 chars)
2. **3 body paragraphs** (max):
   - P1: Business appreciation + co-founder background (combined)
   - P2: Insight + hook question (product-specific)
   - P3: What we built + conviction + 30-min ask
3. **CTA** — Meeting link button matching the segment (DTC or FSD)
4. **"Or just reply here"** — text reply option
5. **No sign-off block** — signature appended by sending platform

**If `--instructions` are provided, apply them as additional personalization.** Instructions take priority over auto-detected choices.

### Step 5: Generate LinkedIn Connection Message

For every outreach brief, generate a warm LinkedIn connection request message. This is especially critical for C-suite and founder contacts where LinkedIn is the primary rapport-building channel.

**LinkedIn message constraints:**
- **Connection request note**: Max 300 characters. Must be punchy, personal, and NOT a pitch.
- **Follow-up message** (after accepted): Max 500 characters. Can introduce Syntropy briefly but still conversational.

**Connection request note guidelines:**
1. Lead with something SPECIFIC about them (not about you)
2. Reference a product, achievement, or journey detail — show you did homework
3. End with a genuine reason to connect (shared interest, not "I want to sell you something")
4. No company pitch, no links, no CTA — just human connection
5. Match the narrative tone (founder-to-founder for Companion, metric-focused for Intelligence)

**Follow-up message guidelines (sent after connection accepted):**
1. Thank them for connecting
2. One sentence about what you noticed / admire about their work
3. One sentence about Syntropy — framed as "thought you'd find this interesting" not a sales pitch
4. Soft ask: "Would love to get your perspective sometime" — no meeting link yet
5. If they respond positively, THEN share the meeting link in the next message

**LinkedIn message templates by narrative:**

| Narrative | Connection Note Tone | Follow-Up Tone |
|-----------|---------------------|----------------|
| **Companion** | Founder-to-founder, admiration for their journey | "Built something I think resonates with what you're doing" |
| **Intelligence** | Respect for their scale/growth | "Working on something in the protocol adherence space — thought you'd want to see the data angle" |
| **Competitive Moat** | Industry peer, shared market observation | "Noticed an opportunity in the protocol space that I think [company] is uniquely positioned for" |
| **Compliance Shield** | Professional respect, regulatory awareness | "Saw the regulatory shifts hitting your space — built a tool that might help" |
| **Platform Extension** | Technical respect, partnership framing | "Your platform + our AI companion could be interesting together" |

Save LinkedIn messages as a markdown section at the bottom of the pre-call brief (`briefs/{company}.md`), under a `## LinkedIn Outreach` heading with two sub-sections: `### Connection Request (300 chars)` and `### Follow-Up After Accepted (500 chars)`.

### Step 6: Save the Email + Update README

Save the personalized email (body-only HTML) to:
```
sales_gtm/outreach/email-templates/H&W DTC - Protocol Retention/warm/{contact-kebab-case}-{company-kebab-case}.html
```

For FSD prospects:
```
sales_gtm/outreach/email-templates/FSD CPG - Food Safety Intelligence/warm/{contact-kebab-case}-{company-kebab-case}.html
```

**Then update the `warm/README.md` index** — add a row to the Personalized Emails table with:
- File name, contact name, title, company, narrative, 3 subject lines, link to brief

The README is the single place for all email metadata (subject lines, recipient info, narrative). The HTML file itself is pure body content for copy-paste.

### Step 7: Report to User

Output a combined summary:

```markdown
## Outreach Brief Ready

**Brief**: sales_gtm/docs/dealflow/briefs/{company}.md
**Email**: sales_gtm/outreach/email-templates/{segment}/warm/{contact}-{company}.html

**Contact**: {Name}, {Title}
**Company**: {Company} ({revenue}, {employees} emp)
**Tier**: {Tier X}
**Narrative**: {Narrative name} (auto-detected | forced)
**Signal Temperature**: {Cold | Warming | Warm | Hot | Very Hot}

### Quick Reference
- **Opener**: {1-sentence summary of email opening}
- **Hook question**: {The specific hard-to-answer question in the email}
- **Key hypothesis**: {1-sentence strongest use-case hypothesis}
- **Primary ask**: {1-sentence ask at close}
- **Meeting link**: {DTC or FSD meeting URL}

### Email Subject Lines
1. {Subject A}
2. {Subject B}
3. {Subject C}

### LinkedIn Messages
- **Connection request**: {The 300-char connection note}
- **Follow-up**: {The 500-char follow-up after accepted}

### Top 3 Products for Protocol
1. {Product} — {protocol fit}
2. {Product} — {protocol fit}
3. {Product} — {protocol fit}

### Recommended Outreach Sequence
1. LinkedIn connection request (Day 0)
2. Email (Day 0 or Day 1 — same day or next day)
3. LinkedIn follow-up after accepted (when accepted)
4. If no email response by Day 3 — second LinkedIn message with value-add

### Next Steps
- [ ] Send LinkedIn connection request
- [ ] Send warm email via Apollo or direct
- [ ] Review the pre-call brief before the meeting
- [ ] Update HubSpot contact record with outreach date
```

## Reference Documents

| Document | Path | Purpose |
|----------|------|---------|
| Call-brief skill | `.claude/skills/call-brief/SKILL.md` | Base workflow (Steps 1-4 of brief generation) |
| Signal flowchart | `sales_gtm/docs/dealflow/signal-flowchart.md` | Narrative selection logic (Section 3) |
| Call scripts | `sales_gtm/docs/dealflow/call-scripts.md` | Question banks, escalation method |
| Operations guide | `sales_gtm/docs/dealflow/operations-guide.md` | Segmentation, deal sizing |
| Pricing | `sales_gtm/docs/company/pricing.md` | Approved pricing phrases only |
| Company profile | `sales_gtm/docs/company/profile.md` | Syntropy Health positioning |
| Warm intro template | `sales_gtm/outreach/email-templates/H&W DTC - Protocol Retention/warm/warm-1-intro.html` | Founder-to-founder warm email base |
| Warm personal template | `sales_gtm/outreach/email-templates/H&W DTC - Protocol Retention/warm/warm-lead-personal.html` | Product-specific warm email base |
| Config | `sales_gtm/packages/booking-worker/src/config.js` | Meeting links, contact info |

## Email Design Rules

1. **Clean, personal, minimal branding** — warm emails should feel like a founder wrote them, not a marketing team
2. **No heavy graphics or logos** — plain white card, subtle border, clean typography
3. **One CTA button** — gradient blue (`#3B82F6 → #2563EB`), links to meeting page
4. **"Or just reply here"** — always include a text reply option below the CTA
5. **No signature block** — appended by sending platform (Apollo/Gmail/HubSpot)
6. **No footer** — signature handles this
7. **Body-only HTML** — no DOCTYPE, html, head, or style tags (stripped for copy-paste)
8. **Preheader text** — product-specific, ~100 chars, hidden from visible email body

## Tone & Voice Guidelines

**Humanity first. We are Syntropy Health — we lead with warmth, not salesmanship.**

- Write like a founder who genuinely admires what they've built — not a BDR running a sequence
- **Open with what you LOVE about their product or mission** — not their job title, not their company size, not their metrics
- Never reference someone's title as a hook ("Chief Customer Officer at a subscription company — retention is literally your job title" = cringe). Reference what they've CREATED instead.
- Show you've used or studied their product — "what I love about Revive is the daily ritual" beats "your subscription model has retention challenges"
- Genuine curiosity about their products and business — ask because you want to know, not because it's a sales tactic
- Never confrontational — frame positively (what brands GAIN, not what they lack)
- **The email should sound like a person you'd want to grab coffee with** — not a person reading from a playbook
- Use [pricing.md](../../sales_gtm/docs/company/pricing.md) approved phrases only
- Reference SPECIFIC products by name — "your Green Tea Peach drops" not "your products"
- One hard-to-answer question per email — not a quiz, a genuine insight that shows you understand their business

## Non-Negotiables

1. **Always research first** — never generate from assumptions
2. **Always name specific products** — generic = lazy
3. **Always include a hook question** — the email should make them think
4. **Always use the meeting link for warm emails** — NOT the intake page
5. **Always use approved pricing language** — reference `company/pricing.md`
6. **Always save both the brief AND the email** — they're a package
7. **Always include 3 subject line variants** — A/B testing is default
8. **Never include dollar amounts in emails** — pricing is a conversation, not an email
9. **Never say "completely free"** — say "free setup for founding partners"
10. **HTML must render in all email clients** — tables-based layout, inline styles, no CSS grid/flex
11. **Never include signature blocks in templates** — no "— Matt", no "Founder, Syntropy Health". Signatures are appended by the sending platform (Apollo/Gmail/HubSpot)

## Subject Line Guidelines

Subject lines are the single highest-leverage element of every outreach email. Generic openers kill open rates.

**Rules:**

1. **Reference a specific business blind spot** — not just the company name. "the post-checkout protocol gap at Pure Essentials" beats "a thought about Pure Essentials"
2. **Use shock value and urgency** — phrases like "invisible churn", "day 12 drop-off", "zero visibility", "silent abandonment", "blind spot", "the metric your stack is missing"
3. **Under 60 characters when possible** — mobile inboxes truncate aggressively
4. **Always keep SUBJECT lines on ONE LINE in the HTML comment header** — no wrapping to the next line. If a subject is too long, shorten it or widen the box
5. **Never use generic openers** — banned patterns:
   - "a thought about [company]"
   - "would love your perspective"
   - "quick question about..."
   - "fellow founder, quick thought on..."
6. **Each subject must be specific to THEIR business** — mention their product names, their customer count, their protocol complexity, their distribution model
7. **Frame around what they CAN'T see** — the value prop is visibility into a blind spot they didn't know they had
