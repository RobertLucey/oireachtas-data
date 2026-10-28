import json
import shutil

from oireachtas_data.bin.validate import main, validate_archive


def _archive(tmp_path):
    archive = tmp_path / "archive"
    month = archive / "debates" / "1919-01" / "1919-01-01_1919-01-31"
    (month / "pages").mkdir(parents=True)
    (month / "reports").mkdir()
    (archive / "members").mkdir()
    (tmp_path / "members").mkdir()
    (archive / "members" / "members.json").write_text(
        json.dumps([{"member": {"pId": "One"}}])
    )
    (tmp_path / "members" / "members.json").write_text(json.dumps([{"pid": "One"}]))

    metadata = {
        "contextDate": "1919-01-22",
        "debateRecord": {
            "uri": "https://data.oireachtas.ie/debate/1",
            "formats": {
                "xml": {"uri": "https://data.oireachtas.ie/report.xml"},
                "pdf": {"uri": "https://data.oireachtas.ie/report.pdf"},
            },
            "debateSections": [
                {"debateSection": {"debateSectionId": "dbsect_1", "showAs": "Prelude"}}
            ],
        },
    }
    entry = {
        "date": "1919-01-22",
        "uri": metadata["debateRecord"]["uri"],
        "files": {
            "xml": "reports/report.xml",
            "pdf": "reports/report.pdf",
        },
    }
    (month / "pages" / "000000.json").write_text(json.dumps({"results": [metadata]}))
    (month / "index.json").write_text(json.dumps([entry]))
    xml = month / "reports" / "report.xml"
    xml.write_text(
        "<debate><debateSection eId='dbsect_1'><summary eId='sum_1'>The House assembled.</summary></debateSection></debate>"
    )
    pdf = month / "reports" / "report.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    return archive, month, xml, pdf, metadata


def test_validate_archive_counts_models_and_members(tmp_path, capsys):
    archive, _, _, _, _ = _archive(tmp_path)

    report = validate_archive(archive)
    serial = validate_archive(archive, workers=1)
    assert report.errors == report.warnings == 0
    assert report.counts == serial.counts
    assert report.counts["debates"] == report.counts["members"] == 1
    assert report.counts["sections"] == report.counts["summaries"] == 1
    assert report.counts["speeches"] == report.counts["paragraphs"] == 0
    assert main(["--archive-dir", str(archive)]) == 0
    assert "1 sections, 1 summaries" in capsys.readouterr().out


def test_parallel_validation_matches_serial(tmp_path):
    archive, month, _, _, _ = _archive(tmp_path)
    shutil.copytree(month, archive / "debates" / "1919-02" / "1919-02-01_1919-02-28")

    serial = validate_archive(archive, workers=1)
    parallel = validate_archive(archive, workers=2)
    assert parallel.counts == serial.counts
    assert parallel.errors == serial.errors
    assert parallel.warnings == serial.warnings
    assert parallel.counts["debates"] == 2


def test_validate_archive_reports_missing_files_and_bad_xml(tmp_path):
    archive, month, xml, pdf, metadata = _archive(tmp_path)
    xml.write_text("<debate>")
    pdf.unlink()
    metadata["debateRecord"]["formats"]["writtens_pdf"] = {
        "uri": "https://data.oireachtas.ie/writtens.pdf"
    }
    (month / "pages" / "000000.json").write_text(json.dumps({"results": [metadata]}))

    report = validate_archive(archive)
    assert report.errors == 2
    assert report.counts["missing_files"] == report.counts["invalid_xml"] == 1
    assert report.counts["unavailable_writtens_pdf"] == 1
    assert main(["--archive-dir", str(archive)]) == 1


def test_validate_archive_rejects_non_pdf_content(tmp_path):
    archive, _, _, pdf, _ = _archive(tmp_path)
    pdf.write_bytes(b"<html>Not a PDF</html>")

    report = validate_archive(archive)
    assert report.counts["invalid_pdf"] == 1
    assert report.errors == 1


def test_validate_archive_reports_malformed_index_path(tmp_path):
    archive, month, _, _, _ = _archive(tmp_path)
    index_path = month / "index.json"
    entries = json.loads(index_path.read_text())
    entries[0]["files"]["xml"] = ["reports/report.xml"]
    index_path.write_text(json.dumps(entries))

    report = validate_archive(archive)
    assert report.errors == 1
    assert "Invalid xml path" in report.error_examples[0]
