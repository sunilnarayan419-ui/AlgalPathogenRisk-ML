"""GEO parser tests. Fixtures are the real series-matrix METADATA (no expression values) and
SYNTHETIC tables built inline."""
import gzip
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.data import geo

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "GSE128981_series_matrix.txt"


def _write_matrix(path, ids, rows, end=True, gz=False, header_cols=None):
    lines = ['!Series_geo_accession\t"GSE_SYN"', "!Sample_geo_accession\t" + "\t".join(f'"{i}"' for i in ids),
             "!Sample_characteristics_ch1\t" + "\t".join('"genotype: x"' for _ in ids),
             "!series_matrix_table_begin",
             "\t".join(['"ID_REF"'] + [f'"{i}"' for i in (header_cols or ids)])]
    lines += ["\t".join(r) for r in rows]
    if end:
        lines.append("!series_matrix_table_end")
    text = "\n".join(lines) + "\n"
    if gz:
        with gzip.open(path, "wt") as fh:
            fh.write(text)
    else:
        path.write_text(text)
    return path


def test_real_metadata_parses_without_expression():
    s = geo.parse_geo_series_matrix(FIXTURE)
    assert s.accession == "GSE128981" and len(s.samples) == 21
    assert s.expression is None and s.provenance["n_expression_rows"] == 0
    assert s.samples["char_genotype"].value_counts().to_dict() == {
        "srta mutant": 11, "SRTA complemented": 6, "SRTA WT": 4}
    assert geo.suitability(s.samples, None)["supports"] == []


@pytest.mark.parametrize("gz", [False, True])
def test_table_parsing_plain_and_gz(tmp_path, gz):
    p = _write_matrix(tmp_path / "m.txt.gz" if gz else tmp_path / "m.txt", ["GSM1", "GSM2"],
                      [['"g1"', "1.5", "2.5"], ['"g2"', "0", "3"]], gz=gz)
    s = geo.parse_geo_series_matrix(p)
    assert s.expression.shape == (2, 2) and s.expression.loc["g1", "GSM2"] == 2.5


def test_truncated_and_misaligned_files_raise(tmp_path):
    with pytest.raises(geo.GeoParseError, match="truncated"):
        geo.parse_geo_series_matrix(_write_matrix(tmp_path / "a.txt", ["GSM1"], [['"g"', "1"]], end=False))
    with pytest.raises(geo.GeoParseError, match="wrong number"):
        geo.parse_geo_series_matrix(_write_matrix(tmp_path / "b.txt", ["GSM1", "GSM2"], [['"g"', "1"]]))
    with pytest.raises(geo.GeoParseError, match="do not match"):
        geo.parse_geo_series_matrix(_write_matrix(tmp_path / "c.txt", ["GSM1"], [['"g"', "1"]],
                                                   header_cols=["GSMX"]))
    (tmp_path / "d.txt").write_text("hello\n")
    with pytest.raises(geo.GeoParseError, match="not a GEO"):
        geo.parse_geo_series_matrix(tmp_path / "d.txt")
    with pytest.raises(FileNotFoundError):
        geo.parse_geo_series_matrix(tmp_path / "missing.txt")


def test_measurement_classification():
    counts = pd.DataFrame(np.random.default_rng(0).integers(0, 5000, (20, 4)))
    fpkm = pd.DataFrame(np.random.default_rng(0).gamma(2, 30, (20, 4)))
    logged = np.log2(fpkm + 1) - 3
    assert geo.classify_measurement(counts)["count_based_methods_valid"] is True
    assert geo.classify_measurement(fpkm)["kind"] == "normalized_abundance_like"
    assert geo.classify_measurement(fpkm)["count_based_methods_valid"] is False
    assert geo.classify_measurement(logged)["kind"] == "log_transformed_like"


def test_qc_flags_duplicates_missing_and_outlier():
    rng = np.random.default_rng(1)
    df = pd.DataFrame(rng.gamma(2, 10, (100, 6)), columns=list("abcdef"),
                      index=[f"g{i}" for i in range(100)])
    df.iloc[:, 5] *= 200  # outlier sample
    df.iloc[0, 0] = np.nan
    df = pd.concat([df, df.iloc[[1]]])  # duplicated gene id
    q = geo.expression_qc(df)
    assert q["n_missing"] == 1 and q["n_duplicate_features"] == 1
    assert "f" in q["outlier_samples_median_robust_z_gt_3.5"]
    with pytest.raises(ValueError):
        geo.expression_qc(pd.DataFrame())
