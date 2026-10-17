# References

Machine-readable register: `references/references.json` (the source of truth). In this revision only the **Neupert et al. 2020** record (PMID 33293544 = doi:10.1038/s41467-020-19983-4, PMC7722844; author list matches the GEO contributors) and the GEO series metadata were re-checked; other entries were carried over from earlier notes and the `verification` field says so. Unverified items
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
| Neupert et al. 2020, *An epigenetic gene silencing pathway selectively acting on transgenic DNA in the green alga Chlamydomonas*, Nat Commun 11:6269, doi:10.1038/s41467-020-19983-4, PMID 33293544 | publication associated with GSE128981; studies transgene silencing, not infection | Verified in this revision (title, DOI, PMID/PMCID, abstract) |
| GEO GSE128981 | dataset | Verified from the supplied series matrix |

Still to source: expected-loss / decision-analysis references for `economics_core.py`, and a methods
reference for enrichment analysis (not implemented).

Data access: series metadata supplied by the user (GEO, public since Oct 2020); check GEO terms before redistributing data files. Access dates are recorded in `data/raw/download_manifest.json` by `scripts/download_geo.py`.
