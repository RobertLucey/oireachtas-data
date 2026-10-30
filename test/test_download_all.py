import datetime as dt
import io
import json
import logging
import tempfile
import threading
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
from oireachtas_data.orm import OireachtasArchive
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
        assert sum(urlsplit(url).path.endswith("/members") for url in urls) == 4
        assert len(urls) >= first_run_requests + 2


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
            assert (month / "incomplete.json").exists()
            assert len(DownloadedDebates(output / "archive")) == 1

            denied = False
            download_all.download_debates(output, date, date, False, False)
            index = json.loads((month / "index.json").read_text())
            assert set(index[0]["files"]) == {"xml", "pdf"}
            assert not (month / "incomplete.json").exists()

            denied = True
            download_all.download_debates(output, date, date, True, False)
            index = json.loads((month / "index.json").read_text())
            assert set(index[0]["files"]) == {"xml", "pdf"}
            assert (month / index[0]["files"]["pdf"]).read_bytes() == b"pdf"


def test_refresh_removes_pages_beyond_new_last_page(tmp_path):
    smaller = False

    def fake_fetch(url):
        offset = int(parse_qs(urlsplit(url).query)["skip"][0])
        if smaller:
            results = [{"id": 0}] if offset == 0 else []
        else:
            results = [{"id": 0}, {"id": 1}] if offset == 0 else [{"id": 2}]
        return json.dumps({"results": results}).encode()

    directory = tmp_path / "pages"
    with (
        patch.object(download_all, "PAGE_SIZE", 2),
        patch.object(download_all, "fetch", side_effect=fake_fetch),
    ):
        assert len(list(download_all.pages("questions", {}, directory, False))) == 3
        assert (directory / "000002.json").exists()
        smaller = True
        assert len(list(download_all.pages("questions", {}, directory, True))) == 1
    assert not (directory / "000002.json").exists()


def test_report_downloads_use_bounded_workers_and_atomic_files(tmp_path):
    simultaneous = threading.Barrier(2)

    def fake_fetch(url):
        if url.endswith("report.xml") or url.endswith("report2.xml"):
            simultaneous.wait(timeout=5)
            return b"<debate/>"
        return json.dumps(
            {
                "results": [
                    {
                        "contextDate": "2024-01-22",
                        "debateRecord": {
                            "uri": "debate/1",
                            "formats": {
                                "xml": {"uri": "https://data.oireachtas.ie/report.xml"}
                            },
                        },
                    },
                    {
                        "contextDate": "2024-01-22",
                        "debateRecord": {
                            "uri": "debate/2",
                            "formats": {
                                "xml": {"uri": "https://data.oireachtas.ie/report2.xml"}
                            },
                        },
                    },
                ]
            }
        ).encode()

    date = dt.date(2024, 1, 22)
    with patch.object(download_all, "fetch", side_effect=fake_fetch):
        download_all.download_debates(tmp_path, date, date, False, False, workers=2)

    directory = tmp_path / "archive" / "debates" / "2024-01" / "2024-01-22_2024-01-22"
    index = json.loads((directory / "index.json").read_text())
    assert len(index) == 2
    assert index[0]["files"] != index[1]["files"]
    for entry in index:
        assert (directory / entry["files"]["xml"]).read_bytes() == b"<debate/>"
    assert not list(directory.rglob("*.part"))


@pytest.mark.parametrize("refresh", [False, True])
def test_shared_report_url_is_fetched_once_with_workers(tmp_path, refresh):
    url = "https://data.oireachtas.ie/report.xml"
    simultaneous = threading.Barrier(2)
    requests = []
    original = download_all.download_report_file

    def arrive_together(*args):
        simultaneous.wait(timeout=5)
        return original(*args)

    def fake_fetch(requested):
        if requested == url:
            requests.append(requested)
            return b"<debate/>"
        return json.dumps(
            {
                "results": [
                    {
                        "contextDate": "2024-01-22",
                        "debateRecord": {
                            "uri": "debate/1",
                            "formats": {"xml": {"uri": url}},
                        },
                    },
                    {
                        "contextDate": "2024-01-22",
                        "debateRecord": {
                            "uri": "debate/2",
                            "formats": {"xml": {"uri": url}},
                        },
                    },
                ]
            }
        ).encode()

    date = dt.date(2024, 1, 22)
    with (
        patch.object(download_all, "fetch", side_effect=fake_fetch),
        patch.object(download_all, "download_report_file", side_effect=arrive_together),
    ):
        download_all.download_debates(tmp_path, date, date, refresh, False, workers=2)
    assert requests == [url]


def test_unavailable_shared_report_url_is_attempted_once(tmp_path, caplog):
    url = "https://data.oireachtas.ie/missing.xml"
    simultaneous = threading.Barrier(2)
    requests = []
    original = download_all.download_report_file

    def arrive_together(*args):
        simultaneous.wait(timeout=5)
        return original(*args)

    def fake_fetch(requested):
        if requested == url:
            requests.append(requested)
            raise HTTPError(url, 403, "Forbidden", {}, None)
        return json.dumps(
            {
                "results": [
                    {
                        "contextDate": "2024-01-22",
                        "debateRecord": {
                            "uri": "debate/1",
                            "formats": {"xml": {"uri": url}},
                        },
                    },
                    {
                        "contextDate": "2024-01-22",
                        "debateRecord": {
                            "uri": "debate/2",
                            "formats": {"xml": {"uri": url}},
                        },
                    },
                ]
            }
        ).encode()

    date = dt.date(2024, 1, 22)
    with (
        patch.object(download_all, "fetch", side_effect=fake_fetch),
        patch.object(download_all, "download_report_file", side_effect=arrive_together),
    ):
        download_all.download_debates(tmp_path, date, date, False, False, workers=2)
    assert requests == [url]
    assert sum(url in message for message in caplog.messages) == 1
    directory = tmp_path / "archive" / "debates" / "2024-01" / "2024-01-22_2024-01-22"
    assert (directory / "incomplete.json").exists()


def test_download_url_is_logged_only_when_fetched(tmp_path, caplog):
    url = "https://data.oireachtas.ie/report.xml"
    caplog.set_level(logging.INFO, logger="download_all")
    with patch.object(
        download_all, "urlopen", return_value=io.BytesIO(b"<debate/>")
    ) as request:
        download_all.download_report_file(url, tmp_path, "xml", refresh=False)
        download_all.download_report_file(url, tmp_path, "xml", refresh=False)
    request.assert_called_once()
    assert caplog.messages.count("Downloading " + url) == 1


def test_downloads_debate_section_documents(tmp_path):
    requested = []

    def fake_fetch(url):
        requested.append(url)
        if url.endswith("section.xml"):
            raise HTTPError(url, 403, "Forbidden", {}, None)
        if url.endswith("section.pdf"):
            return b"pdf"
        if url.endswith("report.xml"):
            return b"<debate/>"
        return json.dumps(
            {
                "results": [
                    {
                        "contextDate": "2024-01-22",
                        "debateRecord": {
                            "uri": "https://data.oireachtas.ie/debate/1",
                            "formats": {
                                "xml": {"uri": "https://data.oireachtas.ie/report.xml"}
                            },
                            "debateSections": [
                                {
                                    "debateSection": {
                                        "debateSectionId": "dbsect_1",
                                        "formats": {
                                            "xml": {
                                                "uri": "https://data.oireachtas.ie/section.xml"
                                            },
                                            "pdf": {
                                                "uri": "https://data.oireachtas.ie/section.pdf"
                                            },
                                        },
                                    }
                                }
                            ],
                        },
                    }
                ]
            }
        ).encode()

    date = dt.date(2024, 1, 22)
    with patch.object(download_all, "fetch", side_effect=fake_fetch):
        download_all.download_debates(tmp_path, date, date, False, False)

    month = tmp_path / "archive" / "debates" / "2024-01" / "2024-01-22_2024-01-22"
    entry = json.loads((month / "index.json").read_text())[0]
    assert (month / entry["files"]["xml"]).is_file()
    assert entry["sections"][0]["id"] == "dbsect_1"
    assert "xml" not in entry["sections"][0]["files"]
    assert (month / entry["sections"][0]["files"]["pdf"]).is_file()
    assert "https://data.oireachtas.ie/section.xml" not in requested
    assert not (month / "incomplete.json").exists()


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
      <references source="#debates">
        <TLCPerson eId="First" href="/ie/oireachtas/member/id/First-Example.D.2020-01-01" showAs="First Example"/>
      </references>
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
    assert first.speeches[0].member_code == "First-Example.D.2020-01-01"
    assert second.speeches[0].member_code is None
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
