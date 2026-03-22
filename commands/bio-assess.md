---
description: Time-boxed assessment mode — structure a 4-hour comp-bio assessment with milestones, checkpoint strategy, and prioritized deliverables.
---

# Bio Assess Command

Manage a time-boxed biological modeling assessment with structured milestones.

## What This Command Does

1. **Parse the assessment prompt** — extract deliverables, constraints, evaluation criteria
2. **Create a phased timeline** — allocate time blocks with hard milestones
3. **Set up checkpoints** — git commits at each milestone for partial credit
4. **Prioritize deliverables** — rank by impact, flag stretch goals vs. must-haves
5. **Monitor progress** — periodic time checks with go/no-go decisions
6. **Prepare submission** — ensure runnable notebook, documented results, clear narrative

## When to Use

- Starting a timed assessment (e.g., Xaira 4-hour take-home)
- Any time-boxed modeling exercise with open-ended components
- When you need to decide what to attempt vs. what to skip under time pressure

## How It Works

### Step 1: Assessment Parsing

Read the prompt and extract:
- **Hard requirements**: what MUST be delivered (e.g., working training loop, results notebook)
- **Evaluation criteria**: what the reviewers care about (thinking process > correct answer)
- **Resources provided**: starter code, data, compute (GPU type, instance details)
- **Ambiguity signals**: "open-ended", "no single correct answer" → show decision-making

### Step 2: Timeline (4-hour template)

```
MILESTONE PLAN (4 hours)
========================

[0:00 - 0:30] SETUP & ORIENTATION
  - Environment setup, data download, read starter notebook
  - Understand data shape, identify key columns
  - Git init, first checkpoint
  → Deliverable: working environment, data loaded

[0:30 - 1:00] EXPLORATION & PLANNING
  - /bio-data: EDA, QC, preprocessing
  - /bio-plan: formulate approach, state hypotheses
  - Identify what's achievable in remaining 3 hours
  → Deliverable: data card, documented plan

[1:00 - 2:30] CORE IMPLEMENTATION
  - /bio-train: implement and train primary model
  - Iterate on architecture if first attempt fails
  - Checkpoint working model at 2:00 mark regardless
  → Deliverable: trained model, training logs

[2:30 - 3:15] EVALUATION & VALIDATION
  - /bio-validate: run biological validation suite
  - /bio-hypothesis: interpret results, state findings
  - Compare against baselines
  → Deliverable: evaluation metrics, interpretation

[3:15 - 3:45] DOCUMENTATION & POLISH
  - Clean notebook: narrative, code comments, figures
  - Document decisions and trade-offs made
  - Record what you would do with more time
  → Deliverable: polished notebook

[3:45 - 4:00] SUBMISSION
  - Final git commit
  - Verify notebook runs end-to-end
  - Submit
  → Deliverable: complete submission
```

### Step 3: Checkpoint Strategy

```bash
# Auto-checkpoint at each milestone
git add -A && git commit -m "checkpoint: setup complete [0:30]"
git add -A && git commit -m "checkpoint: EDA and plan done [1:00]"
git add -A && git commit -m "checkpoint: model trained [2:30]"
git add -A && git commit -m "checkpoint: evaluation complete [3:15]"
git add -A && git commit -m "checkpoint: final submission [4:00]"
```

### Step 4: Prioritization Matrix

| Deliverable | Impact | Time | Priority |
|------------|--------|------|----------|
| Working training loop | HIGH | 1-2h | MUST |
| Data QC & preprocessing | HIGH | 30min | MUST |
| Model evaluation with bio metrics | HIGH | 30min | MUST |
| Clean documented notebook | MEDIUM | 30min | SHOULD |
| Hyperparameter tuning | LOW | 1h+ | COULD |
| Stretch: multiple model comparison | LOW | 2h+ | WON'T (if time-limited) |

### Step 5: Go/No-Go Checkpoints

At each milestone, ask:
- Am I on track? (Yes → continue plan. No → triage)
- Is the current approach working? (Yes → refine. No → pivot to simpler model)
- Do I have a submittable artifact? (No → get to minimum viable result NOW)

**Critical rule**: Always have a submittable result by hour 2. Polish after.

## Example Usage

```
User: /bio-assess Starting the Xaira 4-hour take-home assessment on model training

Agent:
# Assessment Plan: Xaira Model Training Take-Home

## Prompt Analysis
- Task: Open-ended model training on codebase with notebook.ipynb
- Time: 4 hours (hard limit)
- Compute: A10 GPU via SSH on Lambda instance
- Evaluation: How you think about problems > single correct answer

## Key Insight
"Open-ended" + "how you think" → Document your reasoning.
Show trade-offs, state hypotheses, explain decisions.

## Timeline
[0:00-0:30] Setup: SSH, environment, read notebook, load data
[0:30-1:00] EDA: /bio-data, understand the problem space
[1:00-1:15] Plan: /bio-plan, scope what's achievable
[1:15-2:30] Build: /bio-train, implement core model
[2:30-3:15] Eval: /bio-validate + /bio-hypothesis
[3:15-3:45] Polish: narrative, figures, documentation
[3:45-4:00] Submit: verify, commit, submit

## Checkpoints
- Checkpoint 1 (0:30): env working, data loaded ← safety net
- Checkpoint 2 (1:00): EDA done, plan documented
- Checkpoint 3 (2:00): model training (even if not done, save state)
- Checkpoint 4 (2:30): evaluation results
- Checkpoint 5 (4:00): final submission

Starting timer. Current deliverable priority: SETUP.
```

## Arguments

$ARGUMENTS:
- `<assessment-description>` optional — description of the assessment to plan for
