---
name: call-brief
description: Generate a customized pre-call brief and sales script package for a warm lead. Input a contact name, title, and company — outputs a research-backed brief with opening chit-chat, tailored discovery questions, escalation questions, objection handling, and post-call checklist. Saves to sales_gtm/docs/dealflow/briefs/.
origin: project
metadata:
  filePattern: ["**/dealflow/briefs/**", "**/call-scripts*"]
  bashPattern: []
---

# Call Brief Generator

Synthesize a complete pre-call sales package for a warm lead, including company research, personalized call script, and post-call follow-up plan.

## When to Activate

- User says `/call-brief [Contact Name], [Title] at [Company]`
- User asks to "generate a pre-call brief" or "prep for a call with [person]"
- User asks to "create a call package" or "research [company] for a sales call"

## Input Format

```
/call-brief [Contact Name], [Title] at [Company Name]
```

Examples:
- `/call-brief Darren Minton, Chief Executive Officer at Smart for Life`
- `/call-brief Shane Heath, Founder & CEO at MUD\WTR`
- `/call-brief Lynne Gerhards, Owner at Pure Inventions`

## Workflow

### Step 1: Research the Company

Launch a research agent to gather:

1. **Company profile**: products, revenue, employees, founded year, HQ, platform (Shopify?)
2. **Product line**: top 3-5 products with protocol fit assessment (HIGH/MEDIUM/LOW)
3. **Business model**: DTC, subscription, retail, direct sales, wholesale
4. **Tech stack**: Shopify, Klaviyo, ReCharge, Yotpo, etc. (check BuiltWith signals)
5. **Contact background**: LinkedIn, prior roles, education, relevant expertise
6. **Decision authority**: Founder (can sign) vs Champion (needs approval) vs Evaluator
7. **Customer profile**: who buys their products, demographics
8. **Competitive positioning**: how they differentiate
9. **Recent news**: launches, funding, partnerships, leadership changes
10. **Protocol opportunities**: which products have dosing/timing/cycling needs

Use web search and Apollo enrichment (if available) for research.

### Step 2: Determine Narrative & Tier

Based on research, classify:

**Tier:**
- Tier 1: DTC Supplement Founders (1-50 employees) — founder is decision maker
- Tier 2: Scaling DTC Brands (51-500 employees) — VP/Director is decision maker
- Tier 3: Food Safety CPG (10-500 employees) — VP R&D/Quality is decision maker

**Narrative (pick one):**
- **Companion** — DTC founders who need customer engagement / ritual brands
- **Intelligence** — Scaling brands who need retention metrics / data-driven
- **Competitive Moat** — Brands worried about differentiation in crowded market
- **Compliance Shield** — Food safety / regulatory pain
- **Platform Extension** — SaaS companies wanting to embed ShrineAI

Reference: `sales_gtm/docs/dealflow/signal-flowchart.md` §3

### Step 3: Generate the Brief

Use the template at `sales_gtm/docs/dealflow/pre-call-brief.template.md` as the structural guide. Fill every section with research-backed content:

1. **Company Snapshot** — table with all key fields
2. **Contact** — name, title, background, decision authority
3. **Products** — top 3-5 with protocol fit rating and specific protocol opportunities
4. **Intent Signals** — leave blank for user to fill (unless data available from Apollo/HubSpot)
5. **Use-Case Hypotheses** — 2-3 specific hypotheses based on their business model and pain points
6. **Narrative Selection** — which narrative to lead with and why
7. **Opening Chit-Chat** — 2-3 personalized openers based on the contact's background, their products, or recent news. Tone: friendly, genuine, not sycophantic.
8. **Selected Questions** — pre-pick 3 discovery questions and 2-3 escalation questions from the question bank in `call-scripts.md` §3, adapted with [their product] and [their company] filled in
9. **Potential Objections** — 2-3 likely objections based on their profile with tailored responses
10. **Ask at Close** — primary ask (founding partner pilot with specific products named) + fallback ask
11. **Post-Call Checklist** — standard checklist from template

### Step 4: Save the Brief

Save to: `sales_gtm/docs/dealflow/briefs/{company-kebab-case}.md`

Example: `sales_gtm/docs/dealflow/briefs/smart-for-life.md`

### Step 5: Report to User

Output a summary:

```
## Call Brief Ready

**File**: sales_gtm/docs/dealflow/briefs/{company}.md
**Contact**: {Name}, {Title}
**Company**: {Company} ({revenue}, {employees} emp)
**Tier**: {Tier X}
**Narrative**: {Narrative name}

### Quick Reference
- **Opener**: {1-sentence summary of recommended opener}
- **Key hypothesis**: {1-sentence strongest use-case hypothesis}
- **Primary ask**: {1-sentence ask at close}

### Top 3 Products for Protocol
1. {Product} — {protocol fit}
2. {Product} — {protocol fit}
3. {Product} — {protocol fit}
```

## Reference Documents

These documents inform the brief generation:

| Document | Path | Purpose |
|----------|------|---------|
| Pre-call template | `sales_gtm/docs/dealflow/pre-call-brief.template.md` | Structural template |
| Call scripts | `sales_gtm/docs/dealflow/call-scripts.md` | Question banks, escalation method, post-call sequences |
| Signal flowchart | `sales_gtm/docs/dealflow/signal-flowchart.md` | Narrative selection, signal scoring |
| Operations guide | `sales_gtm/docs/dealflow/operations-guide.md` | Segmentation, deal sizing, pricing tiers |
| Pricing | `sales_gtm/docs/company/pricing.md` | Canonical pricing — use approved phrases only |
| Company profile | `sales_gtm/docs/company/profile.md` | Syntropy Health positioning |
| Apollo personas | `sales_gtm/docs/apollo/personas.md` | Buyer persona details |

## Tone & Voice Guidelines

- Friendly but professional — building business relationships, not reading a script
- Genuine curiosity about their products and business
- Never confrontational — frame positively (what brands GAIN, not what they lack)
- "Superpower & helpfulness" tone — glorify capability
- Use [pricing.md](../../sales_gtm/docs/company/pricing.md) approved phrases only — never say "completely free" or "$0 founding partner pricing"

## Non-Negotiables

1. **Always research first** — never generate a brief from assumptions
2. **Always personalize the opener** — generic openers waste the most important 30 seconds
3. **Always pre-pick questions** — don't send someone into a call with "pick from the question bank"
4. **Always name specific products** — "your product" is lazy; "your Green Tea Peach drops" shows homework
5. **Always include a fallback ask** — not every call closes; have a graceful step-down
6. **Always use approved pricing language** — reference `company/pricing.md`
