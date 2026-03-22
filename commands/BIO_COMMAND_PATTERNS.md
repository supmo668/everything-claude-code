# Bio Command Patterns

> Workflow recipes mapping the 7 bio-commands to different assessment scenarios, complexity levels, and project phases.

---

## Quick Reference

| Command | Purpose | When |
|---------|---------|------|
| `/bio-assess` | Time-box management, milestones, checkpoints | **First** — before any code |
| `/bio-plan` | Hypothesis-driven modeling plan | Before implementation |
| `/bio-data` | Data exploration & QC (AnnData/Scanpy) | Before training |
| `/bio-train` | GPU-aware training with bio loss functions | Core modeling |
| `/bio-finetune` | Foundation model adaptation (LoRA/QLoRA) | When using pretrained models |
| `/bio-validate` | Post-modeling biological validation | After training |
| `/bio-hypothesis` | Computational → biological interpretation | Final analysis |

---

## Pattern 1: Timed Assessment (4-Hour Sprint)

**Use case**: Xaira-style take-home, open-ended, GPU-based, 4-hour time limit.

```
/bio-assess  →  /bio-plan  →  /bio-data  →  /bio-train  →  /bio-validate
  0:00-0:15      0:15-0:30     0:30-1:00     1:00-2:30      2:30-3:15
```

| Phase | Commands | Time | Deliverable |
|-------|----------|------|-------------|
| **Setup** | `/bio-assess` | 0:00–0:15 | Timeline, milestones, git init |
| **Scope** | `/bio-plan` | 0:15–0:30 | Hypotheses, loss design, validation plan |
| **Explore** | `/bio-data` | 0:30–1:00 | Data card, QC report, feature selection |
| **Build** | `/bio-train` | 1:00–2:30 | Trained model, loss curves, checkpoints |
| **Evaluate** | `/bio-validate` | 2:30–3:15 | Metrics table, baseline comparison |
| **Document** | `/bio-hypothesis` | 3:15–3:45 | Biological interpretation, evidence scores |
| **Submit** | `checkpoint` | 3:45–4:00 | Final commit, clean notebook |

**Critical rule**: Have a submittable result by hour 2. Use `/bio-assess` checkpoints to enforce this.

---

## Pattern 2: Quick Exploration (1–2 Hours)

**Use case**: Initial data familiarization, QC, deciding what model to build.

```
/bio-data  →  /bio-plan
```

| Step | Command | Focus |
|------|---------|-------|
| 1 | `/bio-data` | Load AnnData, run QC, check batch effects, identify perturbations |
| 2 | `/bio-plan` | Sketch hypotheses and scope — STOP before implementation |

**Skip**: `/bio-assess` (no time constraint), `/bio-train`, `/bio-finetune`, `/bio-validate`

---

## Pattern 3: Standard Training Pipeline (3–5 Hours)

**Use case**: Part 2 (VAE/scVI) or Part 3 (GNN/GEARS) — training a model from scratch.

```
/bio-plan  →  /bio-data  →  /bio-train  →  /bio-validate
```

| Step | Command | Details |
|------|---------|---------|
| 1 | `/bio-plan` | Define loss function (NB-NLL vs MSE+KL), set hypotheses |
| 2 | `/bio-data` | HVG selection, train/val/test split by perturbation |
| 3 | `/bio-train` | A10 config, mixed precision, biological checkpoints |
| 4 | `/bio-validate` | DEG overlap, AUPRC, pathway enrichment, baseline comparison |

**Skip**: `/bio-finetune` (not using pretrained models), `/bio-assess` (no strict time box)

---

## Pattern 4: Foundation Model Finetuning (4–8 Hours)

**Use case**: Part 5 (Geneformer/Evo 2) or Part 3 (scGPT) — adapting pretrained models.

```
/bio-plan  →  /bio-data  →  /bio-finetune  →  /bio-validate  →  /bio-hypothesis
```

| Step | Command | Details |
|------|---------|---------|
| 1 | `/bio-plan` | Choose model, define task (cell classification, perturbation prediction, SNV scoring) |
| 2 | `/bio-data` | Tokenization audit (rank-value for Geneformer, gene2vec for scGPT, byte-level for Evo 2) |
| 3 | `/bio-finetune` | LoRA/QLoRA config, layer freezing, learning rate sweep |
| 4 | `/bio-validate` | Compare finetuned vs zero-shot, check for catastrophic forgetting |
| 5 | `/bio-hypothesis` | Map model predictions to known pathway biology |

**Key**: Use `/bio-finetune` decision tree to choose full vs LoRA vs QLoRA based on model size and A10 memory.

---

## Pattern 5: LLM + RAG Pipeline (3–5 Hours)

**Use case**: Part 4 (BioMistral-7B + RAG) — mechanistic reasoning over literature.

```
/bio-plan  →  /bio-data  →  /bio-train  →  /bio-hypothesis
```

| Step | Command | Adaptation |
|------|---------|------------|
| 1 | `/bio-plan` | Frame as retrieval + reasoning task, define faithfulness metrics |
| 2 | `/bio-data` | Corpus preparation, FAISS index construction, chunk size tuning |
| 3 | `/bio-train` | QLoRA finetuning of BioMistral (use `/bio-finetune` BioMistral section) |
| 4 | `/bio-hypothesis` | LLM-grounded validation, compare RAG output to pathway databases |

**Note**: `/bio-validate` biological metrics (DEG overlap, AUPRC) don't directly apply — use `/bio-hypothesis` evidence scoring instead.

---

## Pattern 6: Dose-Response / Pharmacological Modeling (1–2 Hours)

**Use case**: Part 8 (Hill equation, EC50 estimation).

```
/bio-plan  →  /bio-data  →  /bio-validate
```

| Step | Command | Adaptation |
|------|---------|------------|
| 1 | `/bio-plan` | Define Hill model parameters (E_max, EC50, n), null hypothesis |
| 2 | `/bio-data` | Dose-response data extraction from X-Atlas, QC for dose levels |
| 3 | `/bio-validate` | Curve fit residuals, confidence intervals, cross-compound comparison |

**Skip**: `/bio-train` (curve fitting, not deep learning), `/bio-finetune`

---

## Pattern 7: Capstone Integration (2–3 Hours)

**Use case**: Part 9 — combining results from all parts into end-to-end pipeline.

```
/bio-assess  →  /bio-hypothesis  →  /bio-validate
```

| Step | Command | Focus |
|------|---------|-------|
| 1 | `/bio-assess` | Structure the integration effort, prioritize which parts to combine |
| 2 | `/bio-hypothesis` | Multi-model evidence synthesis, target prioritization scorecard |
| 3 | `/bio-validate` | Cross-method agreement, ensemble metrics, final ranking |

**Key**: No new training — this is synthesis. Use evidence scoring from `/bio-hypothesis`.

---

## Complexity Levels

### Level 1: Beginner (Parts 1, 6)
**Commands**: `/bio-data` → `/bio-validate`
- Focus on data loading, QC, differential expression
- No model training required
- Biological validation = DEG lists, pathway enrichment

### Level 2: Intermediate (Parts 2, 7, 8)
**Commands**: `/bio-plan` → `/bio-data` → `/bio-train` → `/bio-validate`
- Standard model training (VAE, MLP, Hill curve fitting)
- Known architectures, well-defined losses
- Validation against established baselines

### Level 3: Advanced (Parts 3, 4)
**Commands**: `/bio-plan` → `/bio-data` → `/bio-train` or `/bio-finetune` → `/bio-validate` → `/bio-hypothesis`
- Foundation model finetuning, GNN training, RAG pipeline
- Complex loss functions, custom tokenization
- Multi-modal validation (computational + biological interpretation)

### Level 4: Expert (Parts 5, 9)
**Commands**: Full pipeline with `/bio-assess` for time management
- SOTA models (Geneformer, Evo 2), multi-method integration
- Zero-shot vs finetuned comparison, cross-dataset generalization
- End-to-end target discovery scorecard

---

## Combining Bio Commands with ECC Commands

The bio-commands are designed to work alongside existing ECC commands:

| ECC Command | Bio Command Pairing | Purpose |
|-------------|---------------------|---------|
| `/plan` | + `/bio-plan` | General plan structure + biological hypothesis framing |
| `/tdd` | + `/bio-validate` | Test-driven development using biological metrics as test cases |
| `/eval` | + `/bio-validate` | Evaluation harness with bio-meaningful metrics |
| `/checkpoint` | + `/bio-assess` | Git checkpoints aligned with assessment milestones |
| `/loop-start` | + `/bio-train` | Autonomous training loop with biological stopping criteria |
| `/learn` | After any bio-command | Extract reusable bio-modeling patterns as skill files |
| `/claw` | + `/bio-data` | Web research for latest papers on the biological system |

---

## Decision Tree: Which Pattern to Use?

```
Is this a timed assessment?
├── YES → Pattern 1 (Timed Assessment)
└── NO
    ├── Are you finetuning a pretrained model?
    │   ├── YES → Pattern 4 (Foundation Model)
    │   └── NO
    │       ├── Are you building a RAG pipeline?
    │       │   ├── YES → Pattern 5 (LLM + RAG)
    │       │   └── NO
    │       │       ├── Are you training a model?
    │       │       │   ├── YES → Pattern 3 (Standard Training)
    │       │       │   └── NO
    │       │       │       ├── Are you doing integration/synthesis?
    │       │       │       │   ├── YES → Pattern 7 (Capstone)
    │       │       │       │   └── NO → Pattern 2 (Quick Exploration)
    │       │       └── Is it dose-response?
    │       │           └── YES → Pattern 6 (Dose-Response)
    └── Is time-limited? → Add /bio-assess to any pattern
```
