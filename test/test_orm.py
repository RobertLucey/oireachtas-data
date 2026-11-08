import json

import pytest

from oireachtas_data.archive import DownloadedDebates
from oireachtas_data.orm import OireachtasArchive


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _collection(root, name, directory, record, entry):
    path = root / name / directory
    _write_json(path / "pages" / "000000.json", {"results": [record]})
    _write_json(path / "index.json", [entry])
    return path


def test_archive_queries_models_relationships_and_documents(tmp_path):
    root = tmp_path / "archive"
    member_uri = (
        "https://data.oireachtas.ie/ie/oireachtas/member/id/Example.D.2020-01-01"
    )
    member = {
        "member": {
            "uri": member_uri,
            "memberCode": "Example.D.2020-01-01",
            "fullName": "Example Member",
            "memberships": [],
        }
    }
    _write_json(root / "members" / "members.json", [member])
    _write_json(
        root / "houses" / "houses.json",
        [
            {
                "house": {
                    "uri": "house/34",
                    "houseCode": "dail",
                    "houseNo": "34",
                    "showAs": "34th Dáil",
                    "seats": 160,
                    "dateRange": {"start": "2020-02-20", "end": None},
                }
            }
        ],
    )
    _write_json(
        root / "parties" / "parties.json",
        [
            {
                "party": {
                    "uri": "party/1",
                    "partyCode": "Example",
                    "showAs": "Example Party",
                },
                "house": {"uri": "house/34", "showAs": "34th Dáil"},
            }
        ],
    )
    _write_json(
        root / "constituencies" / "constituencies.json",
        [
            {
                "constituencyOrPanel": {
                    "uri": "constituency/1",
                    "representCode": "North",
                    "representType": "constituency",
                    "showAs": "North",
                },
                "house": {"uri": "house/34", "showAs": "34th Dáil"},
            }
        ],
    )

    question_dir = _collection(
        root,
        "questions",
        "2024-01/2024-01-01_2024-01-31",
        {
            "contextDate": "2024-01-22",
            "question": {
                "uri": "question/1",
                "date": "2024-01-22",
                "questionNumber": 1,
                "showAs": "Where is the report?",
                "answerText": "It is here.",
                "questionType": "written",
                "by": {"uri": member_uri},
                "to": {"showAs": "Minister for Example"},
                "debateSection": {"uri": "section/1", "showAs": "Answer"},
            },
        },
        {"uri": "question/1", "files": {"xml": "reports/question.xml"}},
    )
    (question_dir / "reports").mkdir()
    (question_dir / "reports" / "question.xml").write_text("<answer/>")

    vote_dir = _collection(
        root,
        "votes",
        "2024",
        {
            "contextDate": "2024-01-22",
            "division": {
                "uri": "vote/1",
                "date": "2024-01-22",
                "outcome": "Carried",
                "subject": {"showAs": "Example motion"},
                "tallies": {"taVotes": {"members": [{"member": {"uri": member_uri}}]}},
                "debate": {"uri": "debate/1"},
            },
        },
        {"uri": "vote/1", "files": {"pdf": "reports/vote.pdf"}},
    )
    (vote_dir / "reports").mkdir()
    (vote_dir / "reports" / "vote.pdf").write_bytes(b"%PDF-1.7\n")

    bill_dir = _collection(
        root,
        "legislation",
        "2024",
        {
            "bill": {
                "uri": "bill/1",
                "billYear": "2024",
                "billNo": "12",
                "shortTitleEn": "Example Bill",
                "status": "Current",
                "sponsors": [
                    {"sponsor": {"by": {"uri": member_uri}, "isPrimary": True}}
                ],
                "act": {"uri": "act/1", "actYear": "2024", "actNo": "1"},
                "versions": [
                    {"version": {"uri": "version/1", "showAs": "As Initiated"}}
                ],
                "relatedDocs": [],
                "amendmentLists": [],
            },
        },
        {
            "uri": "bill/1",
            "versions": [
                {
                    "uri": "version/1",
                    "files": {"pdf": "reports/versions/bill.pdf"},
                }
            ],
            "relatedDocs": [],
            "amendmentLists": [],
        },
    )
    (bill_dir / "reports" / "versions").mkdir(parents=True)
    (bill_dir / "reports" / "versions" / "bill.pdf").write_bytes(b"%PDF-1.7\n")

    debate_dir = _collection(
        root,
        "debates",
        "2024-01/2024-01-01_2024-01-31",
        {
            "contextDate": "2024-01-22",
            "debateRecord": {
                "uri": "debate/1",
                "chamber": {"showAs": "Dáil Éireann"},
                "debateSections": [{"debateSection": {"debateSectionId": "dbsect_1"}}],
            },
        },
        {"uri": "debate/1", "files": {"xml": "reports/debate.xml"}},
    )
    (debate_dir / "reports").mkdir()
    (debate_dir / "reports" / "debate.xml").write_text(
        "<debate><debateSection eId='dbsect_1'><summary>Hello.</summary></debateSection></debate>"
    )

    db = OireachtasArchive(root)
    question = db.questions.filter(date="2024-01-22").get(uri="question/1")
    assert question.answer_text == "It is here."
    assert question.by.member.full_name == "Example Member"
    assert question.to.name == "Minister for Example"
    assert question.report.xml.read_text() == "<answer/>"
    assert question.metadata["question"]["questionNumber"] == 1

    vote = db.votes.filter(outcome="Carried").first()
    assert vote.subject.name == "Example motion"
    assert vote.ta_members[0].member.full_name == "Example Member"
    assert vote.debate_report.pdf.read_bytes().startswith(b"%PDF-")

    bill = db.bills.filter(year=2024, status="Current").first()
    assert bill.title == "Example Bill"
    assert bill.sponsors[0].member.full_name == "Example Member"
    assert bill.versions[0].pdf.is_file()
    assert bill.act.number == "1"
    assert db.houses.get(uri="house/34").name == "34th Dáil"
    assert db.parties.first().house.name == "34th Dáil"
    assert db.parties.first().house.seats == 160
    assert db.parties.first().house.date_range == {"start": "2020-02-20", "end": None}
    assert db.constituencies.first().name == "North"
    assert db.constituencies.first().house.seats == 160
    assert db.questions.filter(text__contains="report").count() == 1
    assert (
        db.questions.filter(by__member_code="Example.D.2020-01-01").first().uri
        == "question/1"
    )
    assert db.questions.filter(by__member_code="missing").first() is None
    assert (
        db.debates.filter(date="2024-01-22").first().debate_sections[0].content
        == "Hello."
    )
    assert db.debates[0].chamber == "Dáil Éireann"
    assert db.debates.count() == 1
    with pytest.raises(LookupError):
        db.questions.get(uri="missing")


def test_speeches_by_member_scans_debates_lazily(tmp_path):
    root = tmp_path / "archive"
    member_code = "Example.D.2020-01-01"

    def _debate(period, date, xml):
        debate_dir = _collection(
            root,
            "debates",
            period,
            {
                "contextDate": date,
                "debateRecord": {
                    "uri": "debate/" + date,
                    "chamber": {"showAs": "Dáil Éireann"},
                    "debateSections": [
                        {"debateSection": {"debateSectionId": "dbsect_1"}}
                    ],
                },
            },
            {"uri": "debate/" + date, "files": {"xml": "reports/debate.xml"}},
        )
        (debate_dir / "reports").mkdir()
        (debate_dir / "reports" / "debate.xml").write_text(xml)

    _debate(
        "2024-01/2024-01-01_2024-01-31",
        "2024-01-05",
        """<akomaNtoso><debate><debateBody>
          <debateSection eId="dbsect_1"><heading>Opening</heading>
            <speech eId="spk_1" by="#Ex"><p eId="p1">Said something.</p></speech>
          </debateSection>
        </debateBody></debate>
        <references><TLCPerson eId="Ex" href="/ie/oireachtas/member/id/Example.D.2020-01-01"/></references>
        </akomaNtoso>""",
    )
    _debate(
        "2024-02/2024-02-01_2024-02-29",
        "2024-02-10",
        """<akomaNtoso><debate><debateBody>
          <debateSection eId="dbsect_1"><heading>Opening</heading>
            <speech eId="spk_1" by="#Other"><p eId="p1">Someone else.</p></speech>
          </debateSection>
        </debateBody></debate>
        <references><TLCPerson eId="Other" href="/ie/oireachtas/member/id/Someone-Else.D.2019-01-01"/></references>
        </akomaNtoso>""",
    )

    db = OireachtasArchive(root)
    matches = list(db.speeches_by(member_code))
    assert len(matches) == 1
    debate, section, speech = matches[0]
    assert debate.date == "2024-01-05"
    assert section.debate_section_id == "dbsect_1"
    assert speech.content == "\nSaid something."

    # An exact date filter narrows which periods are even opened, not just
    # which results are kept, so this should find nothing without touching
    # the January debate where the member actually spoke.
    assert list(db.speeches_by(member_code, date="2024-02-10")) == []

    # Accepts a Member-like object (anything with .member_code) as well as
    # a bare code string.
    member_stub = type("MemberStub", (), {"member_code": member_code})()
    assert len(list(db.speeches_by(member_stub))) == 1


def test_date_filter_skips_unrelated_months(tmp_path):
    root = tmp_path / "archive"
    _collection(
        root,
        "questions",
        "2024-01/2024-01-01_2024-01-31",
        {
            "question": {"uri": "question/1", "date": "2024-01-22"},
        },
        {"uri": "question/1", "files": {}},
    )
    broken = root / "questions" / "2025-01" / "2025-01-01_2025-01-31"
    (broken / "pages").mkdir(parents=True)
    (broken / "pages" / "000000.json").write_text("invalid JSON")
    _write_json(broken / "index.json", [{"uri": "question/2", "files": {}}])

    db = OireachtasArchive(root)
    assert db.questions.filter(date="2024-01-22").first().uri == "question/1"
    with pytest.raises(json.JSONDecodeError):
        list(db.questions)


def test_debate_xml_is_loaded_only_when_content_is_accessed(tmp_path):
    root = tmp_path / "archive"
    _collection(
        root,
        "debates",
        "2024-01/2024-01-01_2024-01-31",
        {"contextDate": "2024-01-22", "debateRecord": {"uri": "debate/1"}},
        {"uri": "debate/1", "files": {"xml": "reports/missing.xml"}},
    )
    db = OireachtasArchive(root)

    debate = db.debates.filter(date="2024-01-22").first()
    assert debate.uri == "debate/1"
    assert debate.date == "2024-01-22"
    with pytest.raises(FileNotFoundError):
        _ = debate.text
    with pytest.raises(FileNotFoundError):
        _ = debate.debate_sections


def test_overlapping_saved_ranges_prefer_newest_record(tmp_path):
    root = tmp_path / "archive"
    for end, chamber in (("2024-01-21", "Old"), ("2024-01-31", "Updated")):
        _collection(
            root,
            "debates",
            "2024-01/2024-01-01_" + end,
            {
                "contextDate": "2024-01-15",
                "debateRecord": {"uri": "debate/1", "chamber": {"showAs": chamber}},
            },
            {"uri": "debate/1", "files": {}},
        )

    db = OireachtasArchive(root)
    assert db.debates.count() == 1
    assert db.debates.first().chamber == "Updated"
    debates = DownloadedDebates(root)
    assert len(debates) == 1
    assert debates[0].chamber == "Updated"


def test_overlapping_ranges_with_same_end_prefer_wider_range(tmp_path):
    root = tmp_path / "archive"
    for start, chamber in (("2024-01-31", "Old"), ("2024-01-01", "Updated")):
        _collection(
            root,
            "debates",
            "2024-01/" + start + "_2024-01-31",
            {
                "contextDate": "2024-01-31",
                "debateRecord": {"uri": "debate/1", "chamber": {"showAs": chamber}},
            },
            {"uri": "debate/1", "files": {}},
        )

    db = OireachtasArchive(root)
    assert db.debates.count() == 1
    assert db.debates.get(uri="debate/1").chamber == "Updated"
    assert DownloadedDebates(root)[0].chamber == "Updated"
