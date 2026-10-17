from app.services.metadata import audit_geo_series_matrix


def test_detects_gene_rows_when_present(tmp_path):
    txt = ('!Sample_geo_accession\t"GSM1"\n!series_matrix_table_begin\n"ID_REF"\t"GSM1"\n'
           '"g1"\t1.0\n"g2"\t2.0\n!series_matrix_table_end\n')
    p = tmp_path / "m.txt"
    p.write_text(txt)
    r = audit_geo_series_matrix(p)
    assert r["expression_matrix_has_gene_rows"] is True and r["expression_table_gene_rows"] == 2
