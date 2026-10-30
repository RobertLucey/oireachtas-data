import json

from oireachtas_data.bin.find_duplicates import find_duplicate_questions, find_duplicates, main


def test_reports_find_exact_copies_but_skip_same_source_name(tmp_path, capsys):
    reports = tmp_path / "debates" / "2025-01" / "reports"
    reports.mkdir(parents=True)
    first = reports / "xml-one.xml"
    second = reports / "xml-two.xml"
    first.write_bytes(b"same report")
    second.write_bytes(b"same report")
    repeated = tmp_path / "debates" / "2025-02" / "reports" / first.name
    repeated.parent.mkdir(parents=True)
    repeated.write_bytes(b"same report")
    (reports / "xml-other.xml").write_bytes(b"other report")
    (tmp_path / "page.json").write_bytes(b"same report")

    matches = find_duplicates(tmp_path)
    assert len(matches) == 1
    assert matches[0][0] == len(b"same report")
    assert matches[0][2] == sorted((first, second, repeated))
    assert main([str(tmp_path)]) == 1
    assert "1 suspicious duplicate group(s)" in capsys.readouterr().out

    second.unlink()
    assert find_duplicates(tmp_path) == []
    assert len(find_duplicates(tmp_path, include_same_name=True)) == 1
    assert len(find_duplicates(tmp_path, all_files=True)) == 1


def test_same_size_different_content_is_not_duplicate(tmp_path):
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "xml-one.xml").write_bytes(b"one")
    (reports / "xml-two.xml").write_bytes(b"two")
    assert find_duplicates(tmp_path) == []
    assert main([str(tmp_path)]) == 0


def test_matching_samples_still_require_full_file_match(tmp_path):
    reports = tmp_path / "reports"
    reports.mkdir()
    edge = b"a" * (64 * 1024)
    (reports / "xml-one.xml").write_bytes(edge + b"one" + edge)
    (reports / "xml-two.xml").write_bytes(edge + b"two" + edge)
    assert find_duplicates(tmp_path) == []


def test_question_duplicates_ignore_uri_number_and_empty_house_field(tmp_path, capsys):
    pages = tmp_path / "questions" / "2012-07" / "2012-07-01_2012-07-31" / "pages"
    pages.mkdir(parents=True)

    def record(number, uri, answer="Same answer"):
        return {"contextDate": "2012-07-03", "question": {
            "uri": uri,
            "date": "2012-07-03",
            "questionNumber": number,
            "showAs": " 708 Deputy Eoghan Murphy asked about transport. ",
            "answerText": answer,
            "by": {"memberCode": "Eoghan-Murphy.D.2011-03-09"},
            "house": {"committeeCode": ""} if number == 22 else {},
        }}

    uri_22 = "https://data.oireachtas.ie/ie/oireachtas/question/2012-07-03/pq_22"
    uri_708 = "https://data.oireachtas.ie/ie/oireachtas/question/2012-07-03/pq_708"
    (pages / "000000.json").write_text(json.dumps({"results": [record(22, uri_22)]}))
    (pages / "001000.json").write_text(json.dumps({"results": [record(708, uri_708), record(22, uri_22)]}))

    groups = find_duplicate_questions(tmp_path)
    assert len(groups) == 1
    assert {entry[0] for entry in groups[0][3]} == {uri_22, uri_708}
    assert main([str(tmp_path), "--questions"]) == 1
    output = capsys.readouterr().out
    assert "answers match" in output
    assert "1 suspicious duplicate question group(s)" in output

    (pages / "001000.json").write_text(json.dumps({"results": [record(708, uri_708, "Other answer")]}))
    assert main([str(tmp_path), "--questions"]) == 1
    assert "answers differ" in capsys.readouterr().out
