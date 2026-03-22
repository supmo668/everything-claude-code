---
description: Plan a computational biology modeling task with hypothesis-driven structure, objective function design, and validation strategy before writing code.
---

# Bio Plan Command

Plan a comp-bio modeling workflow with scientific rigor before implementation.

## What This Command Does

1. **Parse the biological question** — identify the system, perturbation, and readout
2. **State hypotheses explicitly** — null and alternative, with testable predictions
3. **Design the objective function** — loss terms, regularization, biological priors
4. **Map data assumptions** — sparsity, batch effects, gene program structure, cell-type composition
5. **Plan validation strategy** — held-out perturbations, biologically meaningful metrics (DEG overlap, AUPRC, pathway enrichment)
6. **Estimate compute budget** — GPU memory, training time, checkpoint frequency for time-boxed work
7. **WAIT for user CONFIRM** before proceeding

## When to Use

- Starting any model training or finetuning task on biological data
- Designing a VAE, GNN, or foundation model finetuning pipeline
- Building a perturbation prediction or dose-response model
- When the assessment question is open-ended and requires scoping

## How It Works

1. **Biological Context Audit**
   - What pathway/circuit is being studied? (e.g., mTOR–FOXO3–Senescence)
   - What is the perturbation modality? (CRISPR KO, chemical, dose-titration)
   - What is the readout? (scRNA-seq, bulk expression, phenotype score)

2. **Hypothesis Formulation**
   - H₀: The model cannot distinguish perturbation effects from noise
   - H₁: Latent representations capture biologically coherent perturbation signatures
   - Testable prediction: Top-k predicted DEGs overlap with ground-truth DEGs at >X%

3. **Objective Function Design**
   - Primary loss: reconstruction (MSE/NB-NLL), classification, or contrastive
   - Regularization: KL divergence, sparsity penalty, biological pathway constraints
   - Multi-objective trade-offs: reconstruction vs. disentanglement vs. perturbation separation

4. **Data Assumptions Checklist**
   - [ ] Dropout/zero-inflation handled (scRNA-seq sparsity)
   - [ ] Batch effects accounted for (site, donor, plate)
   - [ ] Highly variable gene selection justified
   - [ ] Train/val/test split respects perturbation identity (no leakage)
   - [ ] Cell-type composition bias considered

5. **Validation & Evaluation Plan**
   - Held-out perturbations (not just held-out cells)
   - Metrics: DEG overlap, AUPRC, R² on mean expression shift, pathway enrichment p-value
   - Baselines: random, PCA, mean-expression predictor
   - Ablations: ±regularization, ±biological priors, latent dimension sweep

6. **Time & Compute Budget**
   - GPU: A10 (24GB) — estimate batch size, model size, training epochs
   - Checkpointing strategy: save every N epochs, early stopping patience
   - Time allocation: data prep (30min), training (2h), evaluation (1h), writeup (30min)

## Example Usage

```
User: /bio-plan I need to train a VAE on Perturb-seq data to learn perturbation-specific latent representations

Agent:
# Bio Plan: VAE for Perturbation Latent Representations

## Biological Context
- System: mTOR–FOXO3–Senescence longevity circuit
- Perturbation: CRISPR gene knockouts (Perturb-seq)
- Readout: scRNA-seq gene expression (AnnData)

## Hypotheses
- H₀: VAE latent space does not separate perturbation conditions
- H₁: Perturbation-specific clusters emerge in latent space
- Prediction: Silhouette score of perturbation clusters > 0.3

## Objective Function
- Reconstruction: Negative binomial NLL (accounts for overdispersion)
- KL regularization: β-VAE with β warmup schedule
- Optional: perturbation classification head on latent z

## Data Assumptions
✓ Using highly variable genes (top 2000)
✓ Log-normalized, batch-corrected via Combat/Harmony
⚠ Need to verify train/val split by perturbation, not by cell

## Validation
- Hold out 20% of perturbations entirely
- Metrics: reconstruction MSE, perturbation silhouette score, DEG recall@50
- Baselines: PCA, scVI default

## Compute (A10, 24GB)
- Model: ~2M params, batch size 256 → ~4GB VRAM
- Estimate: 50 epochs × 3min/epoch = 2.5h
- Checkpoint: every 10 epochs + best val loss

Ready to implement? Type CONFIRM to proceed.
```

## Arguments

$ARGUMENTS:
- `<task-description>` required — natural language description of the modeling task
