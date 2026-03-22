---
description: Fine-tune biological foundation models (Geneformer, scGPT, BioMistral, Evo 2) with domain-aware configuration, tokenization, and evaluation.
---

# Bio Finetune Command

Fine-tune biological foundation models with domain-specific best practices.

## What This Command Does

1. **Select finetuning strategy** — full, LoRA, adapter, head-only based on model + compute budget
2. **Configure tokenization** — rank-value (Geneformer), gene-token (scGPT), BPE (BioMistral), DNA k-mer (Evo 2)
3. **Set hyperparameters** — learning rate, warmup, weight decay tuned for biological finetuning
4. **Design task head** — perturbation prediction, cell-type classification, gene-level regression
5. **Handle biological edge cases** — gene vocabulary mismatches, cell-type imbalance, batch integration
6. **Evaluate with biological metrics** — not just cross-entropy, but DEG recovery, pathway enrichment

## When to Use

- Finetuning Geneformer on perturbation prediction tasks
- Adapting scGPT for cell-state classification
- Running BioMistral for RAG-grounded mechanistic reasoning
- Applying Evo 2 for sequence-level variant effect prediction
- Any transfer learning from pre-trained biological models

## How It Works

### Model-Specific Configurations

#### Geneformer

```python
# Tokenization: rank-value encoding
# Each gene → rank position in cell's expression profile
# Input: ordered gene tokens by expression rank (descending)
config = {
    "model": "ctheodoris/Geneformer",
    "strategy": "LoRA",  # r=8, alpha=16 — 24GB fits easily
    "lr": 2e-5,
    "warmup_ratio": 0.1,
    "epochs": 10,
    "task_head": "perturbation_classification",  # or regression
    "max_input_size": 2048,  # gene tokens per cell
}
# Key: ensure gene vocabulary aligns with your dataset
# Check: adata.var_names ∩ geneformer_vocab → coverage %
```

#### scGPT

```python
config = {
    "model": "scGPT pretrained",
    "strategy": "fine-tune last 4 layers + task head",
    "lr": 1e-4,
    "task": "perturbation_prediction",
    "gene_embedding": "pretrained gene2vec",
    "cell_embedding": "CLS token",
    "batch_key": "donor",  # integrate batch in model
}
# Key: gene tokenization must match pretrained vocabulary
# Use: sc.pp.highly_variable_genes to select gene subset
```

#### BioMistral-7B (for RAG)

```python
config = {
    "model": "BioMistral/BioMistral-7B",
    "strategy": "QLoRA (4-bit)",  # fits on A10
    "lr": 1e-4,
    "task": "mechanistic_reasoning",
    "context": "RAG with FAISS vector store",
    "max_length": 2048,
    "quantization": "bitsandbytes 4-bit (nf4)",
}
# Fits 7B model on A10 with 4-bit quantization
# FAISS index: PubMed abstracts + pathway descriptions
```

#### Evo 2

```python
config = {
    "model": "evo-2 (7B or 40B)",
    "strategy": "zero-shot or LoRA on 7B",
    "task": "variant_effect_prediction",
    "tokenization": "DNA byte-level (single nucleotide)",
    "context_length": 8192,  # or 131k for long-context
}
# 40B requires multi-GPU — use 7B on A10
# Zero-shot: log-likelihood ratio for SNV effects
```

### Finetuning Strategy Decision Tree

```
IF model > 3B params AND GPU < 48GB:
  → QLoRA (4-bit quantization + LoRA)
ELIF model 100M-3B params:
  → LoRA (r=8-16, alpha=2r)
ELIF model < 100M params:
  → Full finetuning
IF task is classification:
  → Freeze backbone, train head first, then unfreeze last N layers
IF data < 1000 samples:
  → Head-only or few-shot, avoid full finetuning
```

### Common Pitfalls

| Issue | Diagnostic | Fix |
|-------|-----------|-----|
| Gene vocab mismatch | Check overlap between adata.var_names and model vocab | Map gene symbols (HGNC), filter to shared genes |
| Catastrophic forgetting | Val loss spikes after epoch 3 | Lower LR, increase warmup, use LoRA |
| Cell-type imbalance | One cell type dominates accuracy | Weighted sampling or focal loss |
| Tokenization errors | Model sees unknown tokens | Verify preprocessing matches model's expected input |
| OOM on A10 | 7B model doesn't fit | Enable 4-bit quantization (QLoRA) |

## Example Usage

```
User: /bio-finetune Adapt Geneformer for perturbation effect prediction on our Perturb-seq data

Agent:
# Finetuning Plan: Geneformer → Perturbation Prediction

## Strategy
- Base model: ctheodoris/Geneformer (30M params)
- Method: LoRA (r=8, alpha=16, dropout=0.05)
- Task head: Linear(256, n_perturbations) for classification

## Data Preparation
- Tokenization: rank-value encoding per cell
- Gene vocab overlap: 94% of HVGs match Geneformer vocabulary
- 6% unmapped genes → drop (non-critical, verified no pathway genes lost)
- 227 perturbations train / 28 val / 29 test

## Training Config
- LR: 2e-5 with cosine schedule
- Warmup: 10% of steps
- Epochs: 10 (early stopping patience=3)
- Batch size: 32 (fits A10 with LoRA)
- Estimated time: ~45 min

## Evaluation Plan
- Primary: perturbation classification accuracy (val set)
- Biological: DEG recall@50 on held-out perturbations
- Comparison: vs. vanilla MLP baseline, vs. PCA+classifier

Starting finetuning setup...
```

## Arguments

$ARGUMENTS:
- `<model-and-task>` optional — which foundation model to finetune and for what task
