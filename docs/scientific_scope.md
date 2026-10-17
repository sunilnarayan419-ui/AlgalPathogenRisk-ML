# Scientific scope

## The data we actually have

GEO **GSE128981** (*C. reinhardtii*, taxid 3055, Illumina HiSeq 4000, polyA RNA-seq, 21 samples, GPL26362)
compares basal transcriptomes of the wild-type parental strain **Elow47** (4), mutants **UVM4** (4) and
**UVM11** (7), and *SRTA*-complemented lines **UVM11-C1** (3) and **UVM11-C9** (3). The associated paper
(Neupert et al. 2020, *Nat Commun*, PMID 33293544) identifies *SRTA* as a sirtuin-type histone deacetylase
that silences **transgenic DNA**. The study concerns transgene silencing in expression strains.

## What it can and cannot support

| Question | Supported? |
|---|---|
| Sample QC, PCA, correlation | Yes, once the expression file is available |
| Exploratory strain/genotype comparisons (log2 FPKM) | Yes, observational; batch is partly confounded |
| Count-based differential expression | Only with raw counts (not in this repository) |
| **Pathogen risk / infection / culture-collapse prediction** | **No.** No outcome labels exist |
| Causal claims about genes | No |

The supplied series-matrix file contains metadata only (an empty expression table); the FPKM file listed in
its header has not been inspected by the authors of this revision.

## Layers kept separate

1. Expression analysis (what was measured) 2. Statistical evidence (DE, FDR) 3. Network analysis (descriptive
structure) 4. Machine learning (software demonstrated on synthetic data) 5. Pathogen-risk assessment (**not
available**) 6. Economic decision support (assumption-driven, hypothetical).

## What real risk prediction would need

A defined endpoint and horizon; independent cultures with measured outcomes (infection, collapse, production
failure); stress/infection conditions; group- and batch-aware validation; external validation; calibration on
held-out data; facility-specific costs. Any pathogen challenge needs biosafety and institutional approval.
