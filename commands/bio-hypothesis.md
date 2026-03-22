---
description: Formulate, test, and document biological hypotheses from model outputs — connecting computational results to mechanistic biological reasoning.
---

# Bio Hypothesis Command

Bridge computational results to biological interpretation with structured hypothesis testing.

## What This Command Does

1. **Extract candidate hypotheses** from model outputs (top perturbations, latent clusters, gene programs)
2. **Ground in known biology** — pathway databases, literature, known gene functions
3. **Design validation experiments** — computational tests to strengthen or reject each hypothesis
4. **Score and rank** hypotheses by evidence strength and novelty
5. **Document reasoning** — create an auditable chain from data → model → hypothesis → evidence

## When to Use

- After model training when interpreting latent representations or predictions
- When ranking drug targets or perturbation effects
- When building a RAG-grounded reasoning pipeline (BioMistral + FAISS)
- For the capstone integration — synthesizing multi-model evidence into a discovery narrative

## How It Works

### Step 1: Hypothesis Extraction

From model outputs, identify:
- **Top-k perturbations** that reverse a disease signature (e.g., senescence)
- **Latent clusters** that correspond to distinct cell states
- **Gene programs** (loadings on latent dimensions) with coherent biological function
- **Unexpected findings** — perturbations with effects opposite to expectation

### Step 2: Biological Grounding

For each candidate hypothesis:

```
Hypothesis: [Gene X] knockout reverses the senescence transcriptomic signature
Evidence FOR:
  - Model: ranked #3 in perturbation effect reversal score
  - Pathway: Gene X is in PI3K-AKT-mTOR pathway (KEGG hsa04150)
  - Literature: PMID:12345678 shows Gene X regulates FOXO3 nuclear translocation
Evidence AGAINST:
  - Gene X is also essential for cell viability (lethal KO in screens)
  - Expression change could be confounded by cell death, not senescence reversal
Confidence: MEDIUM — need to control for viability
```

### Step 3: Computational Validation

Design tests that can be run without wet-lab experiments:
- **Pathway enrichment**: Are top DEGs enriched for expected pathways? (hypergeometric test)
- **Cross-dataset validation**: Does the effect replicate in independent data (e.g., X-Atlas)?
- **Dose-response consistency**: Does effect monotonically increase with perturbation strength?
- **Foundation model agreement**: Does Geneformer in silico deletion agree with model predictions?
- **LLM-grounded check**: Does BioMistral + RAG find mechanistic support in literature?

### Step 4: Evidence Scoring

| Hypothesis | Model Rank | Pathway Match | Literature | Cross-Dataset | Overall |
|-----------|-----------|---------------|-----------|---------------|---------|
| TSC1 KO reverses senescence | #1 | ✅ mTOR | 3 PMIDs | ✅ X-Atlas | ⭐⭐⭐⭐ |
| FOXO3 OE promotes longevity | #4 | ✅ FOXO | 7 PMIDs | ⚠️ weak | ⭐⭐⭐ |
| Novel gene Y involvement | #2 | ❌ unknown | 0 PMIDs | ✅ strong | ⭐⭐ (novel) |

### Step 5: Documentation

Output a structured hypothesis document:

```markdown
# Hypothesis Report: [Project Name]

## Summary
- N hypotheses generated from [model type] on [dataset]
- Top 3 ranked by multi-source evidence

## Hypothesis 1: [Statement]
### Model Evidence
### Pathway Evidence
### Literature Evidence
### Validation Results
### Confidence & Next Steps

## Methods
- Model: [architecture, training details]
- Statistical tests: [enrichment method, multiple testing correction]
- Literature search: [RAG pipeline details, embedding model]
```

## Example Usage

```
User: /bio-hypothesis Interpret the top perturbation effects from my GNN predictions

Agent:
# Hypothesis Report: GNN Perturbation Predictions on mTOR Circuit

## Top Hypotheses

### H1: RPTOR knockout reverses senescence (Confidence: HIGH)
- Model: Ranked #1 in predicted senescence reversal score (z=3.2)
- Pathway: RPTOR is a core mTOR complex 1 component (KEGG hsa04150)
- Literature: Raptor deletion mimics rapamycin treatment (PMID:22153072)
- Validation: DEG overlap with rapamycin profile = 0.41 (p < 1e-6)

### H2: FOXO3 activation signature emerges in cluster 4 (Confidence: MEDIUM)
- Model: Latent cluster 4 shows FOXO3 targets upregulated
- Pathway: FOXO signaling pathway genes enriched (q = 0.003)
- Literature: FOXO3 polymorphisms associated with longevity (PMID:18765803)
- Caution: Cluster also enriched for apoptosis genes — disentangle needed

### H3: Novel role for [Gene Y] in senescence exit (Confidence: LOW-NOVEL)
- Model: Ranked #3 but no known pathway membership
- Action: Run RAG search with BioMistral for mechanistic context
```

## Arguments

$ARGUMENTS:
- `<model-outputs-or-question>` optional — specific model outputs to interpret or biological question to address
