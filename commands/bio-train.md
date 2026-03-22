---
description: Set up and monitor a biological model training run with GPU-aware defaults, biological loss functions, and checkpoint strategy for time-boxed assessments.
---

# Bio Train Command

Configure and launch model training with comp-bio best practices on GPU.

## What This Command Does

1. **Configure training** — architecture, loss, optimizer, scheduler with bio-aware defaults
2. **Set GPU budget** — batch size, gradient accumulation, mixed precision for A10 (24GB)
3. **Implement checkpointing** — save best model + periodic snapshots for time-boxed work
4. **Monitor training** — loss curves, gradient norms, biological metric checkpoints
5. **Handle common failures** — OOM, NaN loss, gradient explosion, CUDA errors

## When to Use

- Training a VAE, GNN, MLP, or finetuning a foundation model on biological data
- When you need to be GPU-memory-aware on a specific card (e.g., A10)
- Under time pressure (4-hour assessment) — need smart early stopping and checkpointing
- When biological loss functions differ from standard ML losses

## How It Works

### Step 1: Architecture Checklist

Before training, verify:
- [ ] Input dimensions match data (n_genes after HVG filtering)
- [ ] Output activation matches data distribution (no activation for expression, sigmoid for binary)
- [ ] Latent dimension justified (10-64 for scRNA-seq VAE, typically 32)
- [ ] Biological priors encoded where appropriate (gene-gene graph for GNN, pathway masks)

### Step 2: Loss Function Selection

| Data Type | Recommended Loss | Rationale |
|-----------|-----------------|-----------|
| scRNA-seq (counts) | Negative Binomial NLL | Models overdispersion in count data |
| scRNA-seq (log-normalized) | MSE + KL (β-VAE) | Standard for normalized expression |
| Perturbation prediction | MSE on mean expression shift | Predicting Δexpression per perturbation |
| Gene classification | Cross-entropy + label smoothing | Noisy biological labels |
| Dose-response | MSE on Hill curve params | Fitting EC50, Emax, slope |

### Step 3: GPU-Aware Configuration (A10, 24GB)

```python
# Estimate VRAM usage
model_params = sum(p.numel() for p in model.parameters())
est_vram_gb = model_params * 4 / 1e9  # float32
batch_vram_gb = batch_size * n_genes * 4 / 1e9

# Safe defaults for A10
config = {
    "batch_size": 256,          # start here, reduce if OOM
    "gradient_accumulation": 1,  # increase if batch_size reduced
    "mixed_precision": True,     # use torch.cuda.amp
    "max_epochs": 100,
    "early_stopping_patience": 10,
    "checkpoint_every_n_epochs": 10,
    "gradient_clip_norm": 1.0,
}
```

### Step 4: Training Monitoring

Every N epochs, log:
- Loss (train + val) — detect divergence early
- Gradient norm — detect explosion/vanishing
- Learning rate — verify scheduler behavior
- **Biological checkpoint**: compute DEG overlap on validation perturbations every 20 epochs

### Step 5: Time-Boxed Strategy

For a 4-hour assessment:
```
Hour 0-0.5: Data loading, EDA, preprocessing
Hour 0.5-1: Architecture setup, sanity check (1 batch overfit test)
Hour 1-3:   Training with checkpointing
Hour 3-3.5: Evaluation and validation (/bio-validate)
Hour 3.5-4: Documentation, results summary, submission
```

### Step 6: Common Failure Recovery

| Symptom | Likely Cause | Quick Fix |
|---------|-------------|-----------|
| OOM on first batch | Batch too large | Halve batch_size, enable AMP |
| NaN loss after epoch 5 | Learning rate too high | Reduce LR by 10×, add gradient clipping |
| Val loss flat, train decreasing | Overfitting | Add dropout, reduce model size, more regularization |
| All predictions identical | Mode collapse (VAE) | Reduce β, use β-warmup, check decoder |
| CUDA error on backward | In-place operation | Replace `x += y` with `x = x + y` |

## Example Usage

```
User: /bio-train Set up VAE training on processed Perturb-seq data

Agent:
# Training Configuration: VAE on Perturb-seq

## Architecture
- Encoder: [2000] → [512] → [256] → [32] (μ, σ)
- Decoder: [32] → [256] → [512] → [2000]
- Activation: ReLU (hidden), None (output)
- Loss: MSE reconstruction + β×KL (β warmup 0→1 over 10 epochs)

## GPU Config (A10)
- Batch size: 256 (~3GB VRAM)
- Mixed precision: enabled (torch.cuda.amp)
- Estimated: ~2M params, well within 24GB

## Training
- Optimizer: Adam (lr=1e-3, weight_decay=1e-5)
- Scheduler: ReduceLROnPlateau (patience=5, factor=0.5)
- Early stopping: patience=10 on val loss
- Checkpoint: every 10 epochs + best val loss

## Sanity Checks
1. Overfit 1 batch first (should reach loss < 0.01)
2. Check gradient norms after epoch 1
3. Verify latent space not collapsed (check KL term > 0)

Starting training...
```

## Arguments

$ARGUMENTS:
- `<model-and-data-description>` optional — what model to train on what data
