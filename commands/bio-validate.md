---
description: Run post-modeling biological validation — check metrics, pathway enrichment, DEG overlap, and flag when results need biological interpretation vs more training.
---

# Bio Validate Command

Validate model outputs against biological ground truth and domain-specific metrics.

## What This Command Does

1. **Compute biological metrics** — DEG overlap, AUPRC, pathway enrichment, silhouette scores
2. **Compare against baselines** — random, PCA, mean-shift predictor
3. **Check for biological plausibility** — known pathway activations, expected gene signatures
4. **Flag red flags** — batch effect leakage, trivial solutions, mode collapse
5. **Recommend next steps** — more training, hyperparameter tuning, or declare success

## When to Use

- After model training completes (VAE, GNN, foundation model finetuning)
- After generating perturbation predictions
- When evaluating whether results are biologically meaningful vs. statistically overfit
- Before writing up results or moving to the next assessment part

## How It Works

### Step 1: Metric Suite

Run the standard comp-bio evaluation battery:

```python
# Core metrics to compute
metrics = {
    "reconstruction": ["MSE", "NB-NLL", "R² per gene"],
    "perturbation_separation": ["silhouette_score", "calinski_harabasz", "perturbation_classification_accuracy"],
    "deg_recovery": ["DEG_overlap@50", "DEG_overlap@100", "AUPRC_deg"],
    "biological_coherence": ["pathway_enrichment_pvalue", "GO_term_overlap", "known_target_rank"],
    "generalization": ["held_out_perturbation_R²", "unseen_combo_correlation"]
}
```

### Step 2: Baseline Comparison

| Model | DEG@50 | AUPRC | Silhouette | R² |
|-------|--------|-------|------------|-----|
| Random | X | X | X | X |
| PCA baseline | X | X | X | X |
| Mean-shift | X | X | X | X |
| **Your model** | **X** | **X** | **X** | **X** |

### Step 3: Red Flag Detection

- **Batch effect leakage**: If silhouette by batch > silhouette by perturbation → data split issue
- **Mode collapse**: If >80% of latent codes cluster in single region → β too high or training issue
- **Trivial solution**: If performance equals mean-shift baseline → model not learning perturbation-specific features
- **Gene list fishing**: If top DEGs are all ribosomal/mitochondrial → QC filtering needed
- **Overfitting**: If train metrics >> held-out metrics by >20% → regularization needed

### Step 4: Decision Framework

```
IF metrics significantly beat baselines AND no red flags:
  → Document results, proceed to next part
IF metrics marginal over baselines:
  → Try: adjust latent dim, β schedule, learning rate, more epochs
IF red flags detected:
  → Fix data pipeline or model architecture BEFORE more training
IF metrics good but biologically implausible:
  → Check: gene filtering, normalization, known positive controls
```

## Example Usage

```
User: /bio-validate Check if my VAE perturbation predictions are biologically meaningful

Agent:
# Biological Validation Report

## Metrics
| Metric | Value | Baseline (PCA) | Status |
|--------|-------|-----------------|--------|
| DEG overlap@50 | 0.34 | 0.12 | ✅ 2.8× baseline |
| AUPRC (DEG) | 0.41 | 0.18 | ✅ Significant |
| Silhouette (perturbation) | 0.28 | 0.15 | ✅ Clear separation |
| R² (held-out) | 0.52 | 0.31 | ✅ Generalizes |

## Red Flag Check
- ✅ Batch silhouette (0.08) < Perturbation silhouette (0.28)
- ✅ Latent space utilization: 89% of dimensions active
- ⚠️ Top DEGs include 3 ribosomal genes — consider filtering

## Recommendation
Results are biologically meaningful. Minor: filter RPL/RPS genes
from DEG evaluation. Ready to proceed to GNN perturbation prediction.
```

## Arguments

$ARGUMENTS:
- `<what-to-validate>` optional — specific model outputs or predictions to check
