# Biological networks

`app.networks.graph.add_edge` requires source database, version, evidence type (experimental/curated/predicted/text_mining) and optional confidence in [0,1]; duplicate edges per (source, interaction type) are rejected; GraphML export/import. No interaction data is bundled.

## Loaders (`app/networks/loaders.py`, written, not executed)

| Source | Function | What each edge means |
|---|---|---|
| STRING `protein.links[.detailed]` | `load_string_links` | *Association confidence* = combined_score/1000. `evidence_type` = dominant channel among experimental / database (curated) / textmining; `predicted` when channels are unavailable or all zero. All channel scores are kept as `score_*` attributes. Not proof of physical interaction. |
| BioGRID TAB3 | `load_biogrid_tab3` | One experimental-evidence edge per (pair, physical or genetic); BioGRID interaction IDs in `evidence_ids`; no confidence reported. |

Behaviour that matters:

* Strict parsing: wrong field counts, non-integer or out-of-range scores, unknown interaction types raise `NetworkLoadError` with line numbers.
* Isoform IDs are collapsed to genes by `default_gene_id` (`3055.Cre01.g000050.t1.1` -> `Cre01.g000050`). Self-pairs and duplicate pairs created by collapsing are counted in the load report; duplicates keep the maximum score.
* **Identifier match is the main risk.** Run `expression_overlap` (done by `scripts/build_network.py --expression`) and do not interpret anything if the overlap fraction is low: it usually means a genome-version or ID-format mismatch. The default STRING download URL in `scripts/download_interactions.py` is unverified; use `--url` if it fails.

```powershell
python scripts\download_interactions.py --taxon 3055 --version v12.0
python scripts\build_network.py --string data\raw\interactions\string_3055_links_detailed_v12.0.txt.gz --string-version v12.0 --min-score 700 --expression data\raw\GSE128981_FPKMs.replicates.v2.tsv.gz
```

Centrality is descriptive, not causal. Enrichment claims need a background universe, identifier mapping and multiple-testing correction (not implemented).
