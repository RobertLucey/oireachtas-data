import datetime as dt
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

import pytest

from oireachtas_data.archive import (
    DownloadedDebates,
    debate_from_record,
    get_downloaded_debates,
)
from oireachtas_data.bin import download_all
from oireachtas_data.models.debate import Debate
from oireachtas_data.models.debate_section import DebateSection
from oireachtas_data.models.para import Para
from oireachtas_data.models.speech import Speech
from oireachtas_data.utils import get_debates, iter_debates


def test_full_download_paginates_and_resumes():
    urls = []

    def fake_fetch(url):
        urls.append(url)
        parsed = urlsplit(url)
        if parsed.hostname == "data.oireachtas.ie":
            return (
                b"<debate>report contents</debate>"
                if parsed.path.endswith(".xml")
                else b"pdf"
            )
        params = parse_qs(parsed.query)
        if parsed.path.endswith("/members"):
            offset = int(params["skip"][0])
            count = 1000 if offset == 0 else 1
            return json.dumps(
                {
                    "results": [
                        {"member": {"pId": str(offset + i), "memberships": []}}
                        for i in range(count)
                    ]
                }
            ).encode()
        return json.dumps(
            {
                "results": [
                    {
                        "contextDate": "2026-10-22",
                        "debateRecord": {
                            "uri": "https://data.oireachtas.ie/debate/1",
                            "chamber": {"showAs": "Dáil Éireann"},
                            "formats": {
                                "xml": {"uri": "https://data.oireachtas.ie/report.xml"},
                                "pdf": {"uri": "https://data.oireachtas.ie/report.pdf"},
                            },
                        },
                    }
                ]
            }
        ).encode()

    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary)
        with patch.object(download_all, "fetch", side_effect=fake_fetch):
            download_all.download_members(output, refresh=False)
            download_all.download_debates(
                output, dt.date(2026, 10, 22), dt.date(2026, 10, 22), False, False
            )
            first_run_requests = len(urls)
            download_all.download_members(output, refresh=False)
            download_all.download_debates(
                output, dt.date(2026, 10, 22), dt.date(2026, 10, 22), False, False
            )

        assert (
            len(json.loads((output / "members" / "members.json").read_text())) == 1001
        )
        assert (
            len(
                json.loads(
                    (output / "archive" / "members" / "members.json").read_text()
                )
            )
            == 1001
        )
        month = output / "archive" / "debates" / "2026-10" / "2026-10-22_2026-10-22"
        assert len(list((month / "reports").iterdir())) == 2
        index = json.loads((month / "index.json").read_text())
        assert set(index[0]["files"]) == {"xml", "pdf"}
        debates = get_downloaded_debates(output / "archive")
        assert len(debates) == 1
        assert type(debates[0]) is Debate
        assert debates[0].text == "report contents"
        assert [debate.date for debate in get_debates(output / "archive")] == [
            "2026-10-22"
        ]
        assert [debate.date for debate in iter_debates(output / "archive")] == [
            "2026-10-22"
        ]
        lazy_debates = DownloadedDebates(output / "archive")
        assert len(lazy_debates) == 1
        assert lazy_debates[0].date == "2026-10-22"
        assert lazy_debates[0] is lazy_debates[0]
        assert first_run_requests == 5
        assert len(urls) == first_run_requests


def test_separate_date_ranges_in_one_month_are_both_loaded():
    def fake_fetch(url):
        date = parse_qs(urlsplit(url).query)["date_start"][0]
        if date == "2026-10-24":
            return json.dumps({"results": []}).encode()
        return json.dumps(
            {
                "results": [
                    {
                        "contextDate": date,
                        "debateRecord": {
                            "uri": "https://data.oireachtas.ie/debate/" + date,
                            "formats": {},
                        },
                    }
                ]
            }
        ).encode()

    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary)
        with patch.object(download_all, "fetch", side_effect=fake_fetch):
            for day in (22, 23, 24):
                date = dt.date(2026, 10, day)
                download_all.download_debates(output, date, date, False, True)

        debates = get_downloaded_debates(output / "archive")
        assert [debate.date for debate in debates] == ["2026-10-22", "2026-10-23"]


def test_denied_report_does_not_stop_download_and_can_be_retried():
    denied = True

    def fake_fetch(url):
        if url.endswith("report.pdf"):
            if denied:
                raise HTTPError(url, 403, "Forbidden", {}, None)
            return b"pdf"
        if url.endswith("report.xml"):
            return b"<debate/>"
        return json.dumps(
            {
                "results": [
                    {
                        "contextDate": "2026-10-22",
                        "debateRecord": {
                            "uri": "https://data.oireachtas.ie/debate/1",
                            "formats": {
                                "xml": {"uri": "https://data.oireachtas.ie/report.xml"},
                                "pdf": {"uri": "https://data.oireachtas.ie/report.pdf"},
                            },
                        },
                    }
                ]
            }
        ).encode()

    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary)
        date = dt.date(2026, 10, 22)
        month = output / "archive" / "debates" / "2026-10" / "2026-10-22_2026-10-22"
        with patch.object(download_all, "fetch", side_effect=fake_fetch):
            download_all.download_debates(output, date, date, False, False)
            index = json.loads((month / "index.json").read_text())
            assert set(index[0]["files"]) == {"xml"}
            assert len(DownloadedDebates(output / "archive")) == 1

            denied = False
            download_all.download_debates(output, date, date, False, False)
            index = json.loads((month / "index.json").read_text())
            assert set(index[0]["files"]) == {"xml", "pdf"}

            denied = True
            download_all.download_debates(output, date, date, True, False)
            index = json.loads((month / "index.json").read_text())
            assert set(index[0]["files"]) == {"xml", "pdf"}
            assert (month / index[0]["files"]["pdf"]).read_bytes() == b"pdf"


def test_download_command_fetches_the_full_archive_only():
    with (
        patch.object(download_all, "download_members") as members,
        patch.object(download_all, "download_debates") as debates,
    ):
        download_all.main([])
        assert members.call_count == 1
        assert debates.call_args.args[1] == dt.date(1919, 1, 1)
        assert debates.call_args.args[2] == dt.date.today()
        assert debates.call_args.args[3:] == (False, False)
        with pytest.raises(SystemExit):
            download_all.main(["--year", "2025"])


def test_archive_xml_builds_debate_speech_and_para_models():
    xml = """<akomaNtoso xmlns="http://docs.oasis-open.org/legaldocml/ns/akn/3.0/CSD13">
      <debate><debateBody>
        <debateSection eId="dbsect_1"><heading>Opening</heading>
          <speech eId="spk_1" by="#First"><p eId="para_1">Hello <i>world</i>.</p></speech>
          <summary eId="sum_1">A decision followed.</summary>
          <debateSection eId="dbsect_2"><heading>Questions</heading>
            <speech eId="spk_2" by="#Second"><p eId="para_2">Another speech.</p></speech>
          </debateSection>
        </debateSection>
      </debateBody></debate>
    </akomaNtoso>"""
    metadata = {
        "contextDate": "2026-10-22",
        "debateRecord": {
            "chamber": {"showAs": "Dáil Éireann"},
            "debateSections": [
                {"debateSection": {"debateSectionId": "dbsect_1", "showAs": "Opening"}},
                {
                    "debateSection": {
                        "debateSectionId": "dbsect_2",
                        "showAs": "Questions",
                    }
                },
            ],
        },
    }
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "debate.xml"
        path.write_text(xml)
        debate = debate_from_record(metadata, {"xml": path})

    assert type(debate) is Debate
    assert len(debate.debate_sections) == 2
    first, second = debate.debate_sections
    assert isinstance(first, DebateSection)
    assert isinstance(first.speeches[0], Speech)
    assert isinstance(first.speeches[0].paras[0], Para)
    assert first.speeches[0].paras[0].content == "Hello world."
    assert len(first.speeches) == len(second.speeches) == 1
    assert second.speeches[0].by == "Second"
    assert first.content == "First: Hello world.\nA decision followed."
    assert first.summaries[0].eid == "sum_1"
    assert second.summaries == []


def test_archive_summaries_fill_sections_without_speeches():
    xml = """<akomaNtoso><debate><debateBody>
      <debateSection eId="dbsect_1"><heading>Prelude</heading>
        <summary eId="sum_1">The House assembled at 12.30 p.m.</summary>
        <summary eId="sum_2">The <i>Roll</i> was called.</summary>
      </debateSection>
    </debateBody></debate></akomaNtoso>"""
    metadata = {
        "contextDate": "1919-01-22",
        "debateRecord": {
            "debateSections": [
                {
                    "debateSection": {
                        "debateSectionId": "dbsect_1",
                        "showAs": "Prelude",
                    }
                }
            ],
        },
    }
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "debate.xml"
        path.write_text(xml)
        debate = debate_from_record(metadata, {"xml": path})

    section = debate.debate_sections[0]
    assert section.speeches == []
    assert [summary.content for summary in section.summaries] == [
        "The House assembled at 12.30 p.m.",
        "The Roll was called.",
    ]
    assert section.content == "The House assembled at 12.30 p.m.\nThe Roll was called."
    assert "\n" not in debate.text
    assert "Prelude The House assembled" in debate.text
