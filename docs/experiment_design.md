# Experimental design

Implemented: sample size for two-group continuous (exact noncentral-t) and binary (Cohen's h) endpoints with attrition and Bonferroni; seeded complete/blocked randomization at the biological-unit level; Welch test with CI and Hedges' g; Benjamini–Hochberg; YAML/Markdown plan export that refuses incomplete specifications.

Unsupported designs (e.g. time-to-event) raise `UnsupportedDesignError`. Any pathogen challenge requires documented biosafety/institutional approval (`biosafety_statement` is a required field).
