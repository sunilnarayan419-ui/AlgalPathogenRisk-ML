from app.services.metadata import audit_geo_series_matrix

def test_metadata_audit(tmp_path):
    content = '!Series_title\t"RNA-Seq expression profiling"\n!Series_geo_accession\t"GSE128981"\n!Sample_title\t"WT rep1"\t"mutant rep1"\n!Sample_geo_accession\t"GSM1"\t"GSM2"\n!series_matrix_table_begin\n"ID_REF"\t"GSM1"\t"GSM2"\n!series_matrix_table_end\n'
    path = tmp_path / "series_matrix.txt"
    path.write_text(content, encoding="utf-8")
    result = audit_geo_series_matrix(path)
    assert result["accession"] == "GSE128981"
    assert result["sample_count_from_titles"] == 2
    assert result["expression_matrix_has_gene_rows"] is False
