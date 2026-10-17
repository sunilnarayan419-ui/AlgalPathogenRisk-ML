# References

Machine-readable register: `references/references.json` (the source of truth). **Verified** means
the title (and, where noted, DOI/PMC/PubMed record) was located in an index during development on
2026-10-17; the `verification_note` field says exactly what was and was not checked. Unverified items
must not be relied on as established evidence.

| Source | Used for | Status |
|---|---|---|
| Conesa et al. 2016, *Genome Biol* 17:13, doi:10.1186/s13059-016-0881-8 | RNA-seq best practice | Verified |
| Love, Huber & Anders 2014, *Genome Biol* 15:550, doi:10.1186/s13059-014-0550-8 | DESeq2 (size factors, NB Wald test) | Verified |
| Muzellec et al. 2023, PyDESeq2 (*Bioinformatics*) | Python implementation used by `count_de.py` | Verified to exist; volume/DOI not recorded |
| Benjamini & Hochberg 1995, *JRSS B* 57:289, doi:10.1111/j.2517-6161.1995.tb02031.x | FDR | Verified (title, DOI) |
| Cohen 1988, *Statistical Power Analysis for the Behavioral Sciences*, 2nd ed. | effect sizes | Verified (catalogue record) |
| Kapoor & Narayanan 2023, *Patterns*, PMC10499856 | data leakage in ML science | Verified (title) |
| Leek et al. 2010, *Nat Rev Genet*, doi:10.1038/nrg2825 | batch effects | Verified (title, DOI) |
| Niculescu-Mizil & Caruana 2005, ICML | probability calibration | Verified (title, venue) |
| Oughtred et al. 2021, BioGRID, PMC7737760 | curated interactions | Verified (title); loader column names unchecked |
| Szklarczyk et al. 2023, STRING, PMC9825434 | association networks | **Not verified** (record found, details from memory) |
| *An epigenetic gene silencing pathway ...*, Nat Commun 2020, doi:10.1038/s41467-020-19983-4 | strain background | Verified to exist; link to PMID 33293544 not independently confirmed |
| GEO GSE128981 | dataset | Verified from the supplied series matrix |

Still to source: expected-loss / decision-analysis references for `economics_core.py`, and a methods
reference for enrichment analysis (not implemented).
