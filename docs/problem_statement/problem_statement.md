# Problem Statement: Algal Culture Vulnerability and Decision Support

**Project:** Algae Culture Vulnerability Prototype\
**Version:** 0.1.0\
**Status:** Research and engineering prototype\
**Primary organism:** *Chlamydomonas reinhardtii*\
**Reference dataset:** NCBI Gene Expression Omnibus (GEO), GSE128981

## 1. Business context

Industrial microalgae cultivation can support the production of
biofuels, proteins, pigments, and other high-value biological products.
Culture performance can be affected by genotype, environmental
conditions, nutrient availability, contamination, and other biological
or process disturbances. A major culture failure can cause lost biomass
or product, wasted inputs, downtime, cleaning costs, and delayed
production.

Operators need reliable ways to characterize biological state and make
economically defensible monitoring and intervention decisions.
Transcriptomic measurements may reveal changes in cellular state, but
converting high-dimensional gene-expression data into a validated
operational risk estimate requires appropriate outcome labels,
representative experiments, careful validation, and calibration to the
intended production setting.

## 2. Core problem

The project will establish a reproducible computational prototype for
processing *C. reinhardtii* transcriptomic data and developing the
software components needed for future biological vulnerability modelling
and decision support.

The initial reference dataset, GSE128981, was designed to compare basal
transcriptomes across wild-type, `srta` mutant, and SRTA-complemented
strains. Its supplied series-matrix file contains sample metadata and an
empty expression-table section; the GEO record points to a separate
supplementary TSV containing replicate FPKM expression values. The
expression file must therefore be obtained and audited before gene-level
modelling.

Importantly, GSE128981 does **not**, based on the supplied metadata,
provide labelled infection events, stress-induced culture collapse, or
industrial production failures. It can support dataset auditing and
carefully scoped exploratory analyses, but it cannot by itself train or
validate a culture-collapse predictor.

## 3. Project objectives

1.  **Data provenance and quality:** Build a repeatable audit for the
    GEO series metadata, sample identifiers, strain/genotype
    annotations, replicate structure, expression matrix dimensions, gene
    identifiers, missing values, and numerical validity.
2.  **Expression data engineering:** Implement modular loading,
    validation, transformation, and export of the supplementary
    expression matrix, with explicit records of input files and
    processing choices.
3.  **Baseline modelling:** Establish a clearly defined exploratory
    baseline task, such as genotype/strain-group classification, only
    after the expression matrix has been verified. Report this
    separately from biological vulnerability prediction.
4.  **Biological evidence integration:** Design interfaces for future
    stress-response, pathogen, and culture-outcome datasets. Keep
    biological pathway or interaction-network analysis optional and
    evidence-traceable.
5.  **Service engineering:** Provide a typed FastAPI interface for
    dataset audits and, when appropriate data become available, model
    inference. Do not return a biological risk probability when no
    validated risk model exists.
6.  **Decision economics:** Implement transparent break-even and
    expected-value calculations for hypothetical interventions, with
    assumptions supplied by the user and sensitivity analysis.
7.  **Reproducibility and quality:** Add automated tests, configuration,
    documentation, and a workflow structure that can later accommodate
    Nextflow for raw sequencing processing.

## 4. Reference dataset and its limits

### Dataset facts from the supplied GEO series-matrix metadata

-   GEO accession: `GSE128981`
-   Organism: *Chlamydomonas reinhardtii*
-   Study topic: RNA-seq expression profiling of `srta` mutant and
    wild-type strains
-   Reported sample groups: Elow47 wild type, UVM4, UVM11, UVM11-C1, and
    UVM11-C9
-   Reported sample count: 21
-   Growth condition in the metadata: mid-log, photo-heterotrophic
    growth
-   Expression format described by GEO: replicate FPKM values in a
    supplementary tab-delimited file
-   Supplementary expression file listed by GEO:\
    `https://ftp.ncbi.nlm.nih.gov/geo/series/GSE128nnn/GSE128981/suppl/GSE128981_FPKMs.replicates.v2.tsv.gz`

The supplied `GSE128981_series_matrix.txt` is primarily metadata. Its
`!series_matrix_table_begin` / `!series_matrix_table_end` section has a
header but no gene-expression rows. The supplementary FPKM TSV is the
required next data artifact for expression-level work.

### Interpretation limits

-   Strain/genotype is not a proxy label for infection or culture
    collapse.
-   FPKM values are already processed expression estimates; they are not
    raw RNA-seq counts. Do not treat them as counts for count-based
    differential-expression tools.
-   The small number of biological samples limits the complexity and
    generalizability of any baseline model.
-   The metadata describes two analysis batches and repeated UVM11
    samples; batch and replicate relationships must be inspected before
    splitting data or evaluating models.
-   The data represent laboratory-grown cultures under the reported
    conditions, not necessarily industrial bioreactors.
-   No operational prevalence, treatment efficacy, intervention cost, or
    culture-loss cost should be inferred from this dataset.

## 5. Proposed technical approach

### Phase A --- Data audit

-   Parse GEO metadata and map each sample accession to its title,
    strain, genotype, and available batch information.
-   Download or obtain the supplementary FPKM TSV from the official GEO
    record.
-   Verify matrix orientation, unique gene identifiers, sample matching,
    data types, missingness, non-finite values, and duplicate records.
-   Produce a machine-readable audit report and a human-readable
    summary.
-   Fail clearly when the expression file is absent or does not match
    the expected schema.

### Phase B --- Expression processing and exploratory analysis

-   Keep raw downloaded files immutable under `data/raw/`.
-   Write validated or transformed matrices to `data/interim/` and
    `data/processed/`.
-   Record transformations such as `log2(FPKM + 1)` explicitly and
    consistently.
-   Explore sample-level distributions, correlations, group structure,
    and potential batch effects.
-   Avoid fitting transformations or selecting features on held-out
    samples during model evaluation.

### Phase C --- Baseline model engineering

-   Define the target and unit of analysis before training.
-   For a provisional genotype/strain task, use a transparent baseline
    and sample-aware validation; describe results as exploratory.
-   Keep feature processing and model fitting inside a scikit-learn
    pipeline to reduce leakage.
-   Do not claim that genotype classification predicts infection, stress
    failure, or culture collapse.
-   Defer Platt calibration and prior-shift correction for biological
    risk until suitable labelled data and a defensible target-population
    prevalence are available.

### Phase D --- Biological risk modelling (future phase)

A genuine culture-vulnerability model requires independent datasets with
measured predictors and outcomes, such as documented stress or infection
exposure followed by defined survival, growth, productivity, or collapse
measurements. The project must define the prediction horizon and outcome
before model development.

Evaluation should include discrimination, calibration, uncertainty,
sensitivity at operational thresholds, and validation across experiments
or batches. External validation is required before operational claims.

### Phase E --- API and economic decision support

-   Expose dataset-audit and health endpoints first.
-   Add inference endpoints only when a compatible, versioned model and
    feature schema exist.
-   For intervention economics, calculate expected loss without
    intervention versus expected loss and treatment cost with
    intervention.
-   Clearly label simulated inputs and assumptions; do not present
    scenario outputs as measured biological effects.
-   Report break-even thresholds and sensitivity to prevalence, failure
    cost, intervention cost, and intervention effectiveness.

## 6. Initial deliverables

1.  GEO metadata audit script and JSON report.
2.  Validated loader for the supplementary FPKM TSV.
3.  Data dictionary and sample manifest.
4.  Exploratory quality-control report.
5.  A baseline analysis with a precisely stated target, if the verified
    data support it.
6.  FastAPI endpoints for health and dataset auditing.
7.  Unit and API tests using pytest.
8.  MkDocs documentation and reproducible setup instructions.
9.  A transparent economic break-even calculator with tests.
10. A documented plan for acquiring suitable outcome-labelled
    stress/infection data.

## 7. Suggested technology stack

  -----------------------------------------------------------------------
  Component               Initial choice          Purpose
  ----------------------- ----------------------- -----------------------
  Data manipulation       pandas, NumPy           Matrix handling and
                                                  validation

  Machine learning        scikit-learn            Baselines and
                                                  leakage-aware pipelines

  API                     FastAPI, Pydantic       Typed service contracts

  Testing                 pytest                  Unit and API-level
                                                  tests

  Biological networks     NetworkX, optional      Exploratory graph
                                                  analysis when a
                                                  traceable interaction
                                                  source is selected

  Workflow orchestration  Nextflow, later phase   Reproducible raw-read
                                                  processing when FASTQ
                                                  inputs are in scope

  Documentation           MkDocs Material         Technical and
                                                  scientific
                                                  documentation

  Web extraction          Scrapy, only if needed  Not required for the
                                                  supplied GEO file;
                                                  prefer official GEO
                                                  resources and endpoints
  -----------------------------------------------------------------------

## 8. Prototype acceptance criteria

The prototype will be considered ready for its initial milestone when:

-   The metadata audit runs reproducibly and identifies the expected
    sample accessions and groups.
-   The system correctly detects that the supplied series-matrix table
    contains no expression rows.
-   The supplementary FPKM matrix can be loaded only after schema,
    sample, and numerical checks pass.
-   Missing files, malformed matrices, duplicate identifiers, and
    invalid numerical values produce clear errors.
-   API health and dataset-audit endpoints return documented, tested
    responses.
-   Economic calculations are deterministic, tested, and explicit about
    assumptions.
-   Documentation distinguishes observed dataset facts, modelling
    assumptions, and future hypotheses.
-   No endpoint or report claims validated culture-collapse prediction
    without suitable labelled outcomes and validation evidence.

## 9. Out of scope for version 0.1

-   Clinical, industrial, or production-grade risk claims.
-   Automatic intervention recommendations for live cultures.
-   Claims that the reference genotype labels indicate infection or
    collapse.
-   Validated prior-shift calibration without source and target
    prevalence evidence.
-   A complete raw-FASTQ workflow before raw-read processing is
    required.
-   Unverified biological interaction edges or unsupported pathway
    claims.

## 10. Scientific and data references

1.  **NCBI GEO: GSE128981.** "RNA-Seq expression profiling of srta
    mutant and WT strains of *Chlamydomonas reinhardtii*."\
    https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE128981
2.  **Supplementary expression matrix listed in the GEO series
    metadata.** `GSE128981_FPKMs.replicates.v2.tsv.gz`\
    https://ftp.ncbi.nlm.nih.gov/geo/series/GSE128nnn/GSE128981/suppl/GSE128981_FPKMs.replicates.v2.tsv.gz
3.  **BioProject PRJNA529641.**\
    https://www.ncbi.nlm.nih.gov/bioproject/PRJNA529641
4.  **SRA study SRP189733.**\
    https://www.ncbi.nlm.nih.gov/sra?term=SRP189733

The GEO record lists PubMed identifier `33293544`; retrieve and review
the associated paper before making biological interpretations or
selecting candidate stress-response features.

------------------------------------------------------------------------

**Prototype principle:** Build a reproducible data and software
foundation first. Treat culture-collapse prediction as a future
hypothesis that must be supported by outcome-labelled experiments, not
as a capability already established by GSE128981.
