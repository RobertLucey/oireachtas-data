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


def test_current_month_rerun_updates_questions_without_duplicates(tmp_path):
    today = dt.date.today()
    first = today.replace(day=1)
    calls = 0

    def fake_fetch(url):
        nonlocal calls
        calls += 1
        results = [
            {
                "contextDate": today.isoformat(),
                "question": {
                    "uri": "question/1",
                    "answerText": "Updated" if calls == 2 else "Old",
                },
            }
        ]
        if calls == 2:
            results.append(
                {
                    "contextDate": today.isoformat(),
                    "question": {
                        "uri": "question/2",
                        "answerText": "New",
                    },
                }
            )
        return json.dumps({"results": results}).encode()

    with patch.object(download_all, "fetch", side_effect=fake_fetch):
        download_all.download_questions(tmp_path, today, today, refresh=False)
        download_all.download_questions(tmp_path, first, today, refresh=False)

    db = OireachtasArchive(tmp_path / "archive")
    assert calls == 2
    assert db.questions.count() == 2
    assert db.questions.get(uri="question/1").answer_text == "Updated"
    assert db.questions.get(uri="question/2").answer_text == "New"
    month_dir = download_all.month_directory(tmp_path, "questions", first, today)
    assert (month_dir / "index.json").is_file()


def test_current_year_rerun_updates_votes_and_legislation(tmp_path):
    today = dt.date.today()
    calls = {"votes": 0, "legislation": 0}

    def fake_fetch(url):
        collection = urlsplit(url).path.rsplit("/", 1)[-1]
        calls[collection] += 1
        if collection == "votes":
            results = [{"division": {"uri": "vote/1", "outcome": "Updated"}}]
            if calls[collection] == 2:
                results.append({"division": {"uri": "vote/2"}})
        else:
            results = [
                {
                    "bill": {
                        "uri": "bill/1",
                        "billYear": str(today.year),
                        "status": "Updated",
                        "versions": [],
                    }
                }
            ]
            if calls[collection] == 2:
                results.append(
                    {
                        "bill": {
                            "uri": "bill/2",
                            "billYear": str(today.year),
                            "versions": [],
                        }
                    }
                )
        return json.dumps({"results": results}).encode()

    with patch.object(download_all, "fetch", side_effect=fake_fetch):
        for _ in range(2):
            download_all.download_votes(tmp_path, today, today, refresh=False)
            download_all.download_legislation(
                tmp_path, today.year, today.year, refresh=False
            )

    db = OireachtasArchive(tmp_path / "archive")
    assert calls == {"votes": 2, "legislation": 2}
    assert db.votes.count() == db.bills.count() == 2
    assert db.votes.get(uri="vote/1").outcome == "Updated"
    assert db.bills.get(uri="bill/1").status == "Updated"


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


def test_completed_historical_period_is_skipped_without_reading_pages(tmp_path):
    date = dt.date(2024, 1, 22)
    with patch.object(
        download_all,
        "fetch",
        return_value=json.dumps(
            {"results": [{"contextDate": date.isoformat(), "question": {"uri": "q/1"}}]}
        ).encode(),
    ):
        download_all.download_questions(tmp_path, date, date, refresh=False)
    index_path = (
        tmp_path
        / "archive"
        / "questions"
        / "2024-01"
        / "2024-01-22_2024-01-22"
        / "index.json"
    )
    original = index_path.read_bytes()
    with patch.object(
        download_all, "pages", side_effect=AssertionError("read cached pages")
    ):
        download_all.download_questions(tmp_path, date, date, refresh=False)
    assert index_path.read_bytes() == original


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


def test_download_command_fetches_the_full_archive_only():
    with (
        patch.object(download_all, "download_members") as members,
        patch.object(download_all, "download_reference_data") as references,
        patch.object(download_all, "download_debates") as debates,
        patch.object(download_all, "download_questions") as questions,
        patch.object(download_all, "download_votes") as votes,
        patch.object(download_all, "download_legislation") as legislation,
    ):
        download_all.main([])
        assert members.call_count == 1
        assert references.call_count == 1
        assert debates.call_args.args[1] == dt.date(1919, 1, 1)
        assert debates.call_args.args[2] == dt.date.today()
        assert debates.call_args.args[3:] == (False, False)
        assert questions.call_args.args[1:3] == (dt.date(1980, 1, 1), dt.date.today())
        assert votes.call_args.args[1:3] == (dt.date(1919, 1, 1), dt.date.today())
        assert legislation.call_args.args[1:3] == (1919, dt.date.today().year)
        assert debates.call_args.kwargs["workers"] == 4
        download_all.main(["--workers", "2"])
        assert questions.call_args.kwargs["workers"] == 2
        with pytest.raises(SystemExit):
            download_all.main(["--year", "2025"])
        with pytest.raises(SystemExit):
            download_all.main(["--workers", "0"])


def test_download_command_can_select_only_debates():
    with (
        patch.object(download_all, "download_members") as members,
        patch.object(download_all, "download_reference_data") as references,
        patch.object(download_all, "download_debates") as debates,
        patch.object(download_all, "download_questions") as questions,
        patch.object(download_all, "download_votes") as votes,
        patch.object(download_all, "download_legislation") as legislation,
    ):
        download_all.main(["--collections", "debates"])
    debates.assert_called_once()
    for skipped in (members, references, questions, votes, legislation):
        skipped.assert_not_called()


def test_downloads_additional_collections_and_linked_documents(tmp_path):
    requests = []

    def fake_fetch(url):
        requests.append(url)
        parsed = urlsplit(url)
        if parsed.hostname == "data.oireachtas.ie":
            return b"<akomaNtoso/>" if parsed.path.endswith(".xml") else b"%PDF-1.7\n"
        params = parse_qs(parsed.query)
        if parsed.path.endswith("/houses"):
            results = [
                {"house": {"houseCode": "dail", "houseNo": "33"}},
                {"house": {"houseCode": "dail", "houseNo": "34"}},
            ]
        elif parsed.path.endswith("/parties"):
            assert params["chamber"] == ["dail"]
            results = [
                {
                    "party": {
                        "uri": "https://data.oireachtas.ie/party/"
                        + params["house_no"][0]
                    }
                }
            ]
        elif parsed.path.endswith("/constituencies"):
            assert params["chamber"] == ["dail"]
            results = [
                {
                    "constituencyOrPanel": {
                        "uri": "https://data.oireachtas.ie/constituency/"
                        + params["house_no"][0]
                    }
                }
            ]
        elif parsed.path.endswith("/questions"):
            assert params["show_answers"] == ["true"]
            results = [
                {
                    "contextDate": "2024-01-22",
                    "question": {
                        "uri": "https://data.oireachtas.ie/question/1",
                        "answerText": "The answer.",
                        "debateSection": {
                            "formats": {
                                "xml": {
                                    "uri": "https://data.oireachtas.ie/question.xml"
                                }
                            }
                        },
                    },
                }
            ]
        elif parsed.path.endswith("/votes"):
            results = [
                {
                    "contextDate": "2024-01-22",
                    "division": {
                        "uri": "https://data.oireachtas.ie/vote/1",
                        "tallies": {"taVotes": {"tally": 1}},
                        "debate": {
                            "formats": {
                                "pdf": {"uri": "https://data.oireachtas.ie/vote.pdf"}
                            }
                        },
                    },
                }
            ]
        elif parsed.path.endswith("/legislation"):
            assert params["bill_year"] == ["2024"]
            results = [
                {
                    "bill": {
                        "uri": "https://data.oireachtas.ie/bill/1",
                        "billYear": "2024",
                        "versions": [
                            {
                                "version": {
                                    "uri": "https://data.oireachtas.ie/version/1",
                                    "formats": {
                                        "pdf": {
                                            "uri": "https://data.oireachtas.ie/version.pdf"
                                        }
                                    },
                                }
                            }
                        ],
                        "relatedDocs": [
                            {
                                "relatedDoc": {
                                    "uri": "https://data.oireachtas.ie/doc/1",
                                    "formats": {
                                        "xml": {
                                            "uri": "https://data.oireachtas.ie/doc.xml"
                                        }
                                    },
                                }
                            }
                        ],
                        "amendmentLists": [
                            {
                                "amendmentList": {
                                    "formats": {
                                        "pdf": {
                                            "uri": "https://data.oireachtas.ie/amendment.pdf"
                                        }
                                    }
                                }
                            }
                        ],
                    }
                }
            ]
        else:
            raise AssertionError(url)
        return json.dumps({"results": results}).encode()

    first = last = dt.date(2024, 1, 22)
    with patch.object(download_all, "fetch", side_effect=fake_fetch):
        download_all.download_reference_data(tmp_path, refresh=False)
        download_all.download_questions(tmp_path, first, last, refresh=False)
        download_all.download_votes(tmp_path, first, last, refresh=False)
        download_all.download_legislation(tmp_path, 2024, 2024, refresh=False)
        first_requests = len(requests)
        download_all.download_reference_data(tmp_path, refresh=False)
        download_all.download_questions(tmp_path, first, last, refresh=False)
        download_all.download_votes(tmp_path, first, last, refresh=False)
        download_all.download_legislation(tmp_path, 2024, 2024, refresh=False)

    assert len(requests) == first_requests + 5  # Current reference collections refresh.
    archive = tmp_path / "archive"
    assert len(json.loads((archive / "houses" / "houses.json").read_text())) == 2
    assert len(json.loads((archive / "parties" / "parties.json").read_text())) == 2
    assert (
        len(
            json.loads((archive / "constituencies" / "constituencies.json").read_text())
        )
        == 2
    )
    question_dir = archive / "questions" / "2024-01" / "2024-01-22_2024-01-22"
    question = json.loads((question_dir / "index.json").read_text())[0]
    assert (question_dir / question["files"]["xml"]).is_file()
    assert (
        json.loads((question_dir / "pages" / "000000.json").read_text())["results"][0][
            "question"
        ]["answerText"]
        == "The answer."
    )
    vote_dir = archive / "votes" / "2024"
    vote = json.loads((vote_dir / "index.json").read_text())[0]
    assert (vote_dir / vote["files"]["pdf"]).read_bytes().startswith(b"%PDF-")
    bill_dir = archive / "legislation" / "2024"
    bill = json.loads((bill_dir / "index.json").read_text())[0]
    for collection, kind in (
        ("versions", "pdf"),
        ("relatedDocs", "xml"),
        ("amendmentLists", "pdf"),
    ):
        assert (bill_dir / bill[collection][0]["files"][kind]).is_file()


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
