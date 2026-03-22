---
description: Explore, QC, and preprocess biological datasets (scRNA-seq, Perturb-seq, AnnData) with domain-aware checks for sparsity, batch effects, and gene filtering.
---

# Bio Data Command

Domain-aware data exploration and preprocessing for biological datasets.

## What This Command Does

1. **Load and inspect** AnnData/scRNA-seq datasets — shape, sparsity, metadata
2. **Run QC checks** — mitochondrial %, ribosomal %, doublet detection, library size
3. **Identify batch effects** — donor, plate, experimental condition covariates
4. **Select informative features** — highly variable genes, pathway-based gene sets
5. **Verify data integrity** — no leakage between train/val/test splits, perturbation coverage
6. **Generate a data card** — summary statistics for reproducibility

## When to Use

- First encounter with a new biological dataset
- Before any model training on scRNA-seq / Perturb-seq data
- When debugging unexpected model behavior (check data first)
- When loading X-Atlas or other large perturbation atlases

## How It Works

### Step 1: Dataset Inspection

```python
import scanpy as sc
import anndata as ad

adata = sc.read_h5ad("data.h5ad")
print(f"Cells: {adata.n_obs:,}, Genes: {adata.n_vars:,}")
print(f"Sparsity: {1 - adata.X.nnz / (adata.n_obs * adata.n_vars):.1%}")
print(f"Obs columns: {list(adata.obs.columns)}")
print(f"Perturbations: {adata.obs['perturbation'].nunique()}")
```

### Step 2: QC Metrics

```python
sc.pp.calculate_qc_metrics(adata, qc_vars=["mt", "ribo"], inplace=True)
# Flag cells: >20% mito, <200 genes, >5000 genes
# Flag genes: expressed in <10 cells
```

### Step 3: Batch Effect Assessment

- UMAP colored by batch vs. perturbation — visual check
- Silhouette score by batch covariate
- If batch silhouette > 0.2 → recommend batch correction (Harmony, scVI batch key)

### Step 4: Feature Selection

- Highly variable genes: `sc.pp.highly_variable_genes(n_top_genes=2000)`
- Cross-check: do HVGs include known pathway genes (mTOR, FOXO3, MTOR, TSC1, TSC2)?
- If key genes excluded → consider union of HVG + pathway gene set

### Step 5: Split Validation

- Verify train/val/test split is by **perturbation**, not by cell
- Check perturbation representation: min cells per perturbation in each split
- Flag perturbations with <50 cells (underpowered)

### Step 6: Data Card Output

```
DATASET CARD
============
Source: [filename]
Cells: X | Genes: Y | Perturbations: Z
Sparsity: X% | Median genes/cell: Y | Median UMI/cell: Z
QC filtered: X cells removed (Y%)
Batch covariates: [list]
HVG count: 2000 | Pathway genes retained: Y/N
Split: train X% / val Y% / test Z% (by perturbation)
```

## Example Usage

```
User: /bio-data Explore the Perturb-seq dataset before training

Agent:
# Data Exploration Report

## Dataset Overview
- Cells: 48,231 | Genes: 18,752 | Perturbations: 284
- Sparsity: 94.2% (typical for scRNA-seq)
- Metadata: perturbation, cell_type, donor, plate, n_genes

## QC Results
- Removed 2,341 cells (4.9%): high mito (>20%) or low genes (<200)
- Removed 4,112 genes: expressed in <10 cells
- Post-QC: 45,890 cells × 14,640 genes

## Batch Assessment
- 3 donors, 6 plates → batch silhouette = 0.11 (mild)
- Recommendation: include batch key in model, no aggressive correction needed

## Feature Selection
- 2,000 HVGs selected
- ✅ MTOR, FOXO3, TSC1, TSC2, RPTOR all in HVG set
- ⚠️ AKT1 not in HVGs — adding via pathway union

## Split Strategy
- 227 perturbations train / 28 val / 29 test
- Min cells per perturbation: 41 (adequate)
- No perturbation appears in multiple splits ✅
```

## Arguments

$ARGUMENTS:
- `<dataset-path-or-description>` optional — path to h5ad file or description of dataset to explore
