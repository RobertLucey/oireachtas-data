"""Download Oireachtas API records and their linked reports."""

import argparse
import datetime as dt
import hashlib
import json
import logging
import os
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from itertools import islice
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from oireachtas_data.constants import OIREACHTAS_DIR
from oireachtas_data.models.member import Member


API_URL = "https://api.oireachtas.ie/v1"
PAGE_SIZE = 1000
FIRST_DEBATE = dt.date(1919, 1, 1)
FORMAT_KINDS = ("xml", "pdf", "writtens_pdf")
COLLECTIONS = ("members", "debates")
LOG = logging.getLogger("download_all")


def fetch(url):
    """Fetch a URL, retrying temporary API and network failures."""
    LOG.info("Downloading %s", url)
    for attempt in range(5):
        try:
            with urlopen(
                Request(url, headers={"Accept": "*/*"}), timeout=60
            ) as response:
                return response.read()
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 4:
                raise
        except URLError:
            if attempt == 4:
                raise
        delay = min(2**attempt, 16)
        LOG.warning("Request failed; retrying %s in %s seconds", url, delay)
        time.sleep(delay)
    raise RuntimeError("Request failed: " + url)


def save_bytes(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=path.parent, prefix=path.name + ".", suffix=".part", delete=False
    ) as handle:
        temporary = Path(handle.name)
    try:
        temporary.write_bytes(data)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def api_page(endpoint, params, path, refresh):
    if path.exists() and not refresh:
        data = json.loads(path.read_text(encoding="utf-8"))
    else:
        url = API_URL + "/" + endpoint + "?" + urlencode(params)
        data = json.loads(fetch(url))
        if not isinstance(data, dict) or not isinstance(data.get("results"), list):
            raise ValueError(
                "Unexpected API response for " + url + ": " + str(data)[:300]
            )
        save_bytes(path, json.dumps(data, ensure_ascii=False).encode("utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        raise ValueError("Invalid cached API page: " + str(path))
    return data["results"]


def pages(endpoint, params, directory, refresh):
    skip = 0
    while True:
        page = api_page(
            endpoint,
            dict(params, limit=PAGE_SIZE, skip=skip),
            directory / ("%06d.json" % skip),
            refresh,
        )
        LOG.info("%s: %s records at offset %s", endpoint, len(page), skip)
        for record in page:
            yield record
        if len(page) < PAGE_SIZE:
            if refresh:
                for stale in directory.glob("[0-9][0-9][0-9][0-9][0-9][0-9].json"):
                    if int(stale.stem) > skip:
                        stale.unlink()
            break
        skip += PAGE_SIZE


def month_ranges(start, end):
    cursor = start.replace(day=1)
    while cursor <= end:
        next_month = (cursor + dt.timedelta(days=32)).replace(day=1)
        yield max(cursor, start), min(next_month - dt.timedelta(days=1), end)
        cursor = next_month


def year_ranges(start, end):
    for year in range(start.year, end.year + 1):
        yield max(start, dt.date(year, 1, 1)), min(end, dt.date(year, 12, 31))


def month_directory(output, collection, first, last):
    # Keep the active month at one path as its API date_end advances each day.
    today = dt.date.today()
    if first.day == 1 and (first.year, first.month) == (today.year, today.month):
        last_in_month = (first + dt.timedelta(days=32)).replace(day=1) - dt.timedelta(
            days=1
        )
        directory_end = last_in_month
    else:
        directory_end = last
    return (
        output
        / "archive"
        / collection
        / first.strftime("%Y-%m")
        / (first.isoformat() + "_" + directory_end.isoformat())
    )


class ReportFetchState:
    """Coordinate report requests shared by records in one download run."""

    def __init__(self):
        self.locks = [threading.Lock() for _ in range(128)]
        self.attempts = {}


def download_report_file(url, directory, kind, refresh, state=None):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "data.oireachtas.ie":
        raise ValueError("Unexpected report URL: " + url)
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    path = directory / (kind + "-" + digest + (".xml" if kind == "xml" else ".pdf"))
    state = state or ReportFetchState()
    with state.locks[int(digest[:8], 16) % len(state.locks)]:
        previous = state.attempts.get(path)
        if previous is not None and previous is not True:
            cached_error = HTTPError(url, previous, "Unavailable", None, None)
            cached_error.cached = True
            raise cached_error
        if path.exists() and (not refresh or previous is True):
            return path
        try:
            save_bytes(path, fetch(url))
        except HTTPError as exc:
            if exc.code in (403, 404, 410) and path.exists():
                state.attempts[path] = True
                LOG.warning(
                    "Could not refresh %s (%s); keeping saved file", url, exc.code
                )
            else:
                if exc.code in (403, 404, 410):
                    state.attempts[path] = exc.code
                raise
        else:
            state.attempts[path] = True
    return path


def download_formats(formats, directory, refresh, description, state=None):
    """Save available XML/PDF links in a report directory."""
    if not isinstance(formats, dict):
        return {}, 0
    saved = {}
    unavailable = 0
    for kind in FORMAT_KINDS:
        format_data = formats.get(kind) or {}
        url = format_data.get("uri") if isinstance(format_data, dict) else None
        if not url:
            continue
        try:
            path = download_report_file(url, directory, kind, refresh, state)
        except HTTPError as exc:
            if exc.code not in (403, 404, 410):
                raise
            unavailable += 1
            if not getattr(exc, "cached", False):
                LOG.warning(
                    "Skipping unavailable %s for %s (%s): %s",
                    kind,
                    description,
                    exc.code,
                    url,
                )
        else:
            saved[kind] = path.name
    return saved, unavailable


def _save_linked_files(
    formats, record_dir, subdirectory, refresh, description, state=None
):
    saved, unavailable = download_formats(
        formats, record_dir / subdirectory, refresh, description, state
    )
    paths = {kind: str(Path(subdirectory) / name) for kind, name in saved.items()}
    return paths, unavailable


def _write_index(path, records):
    save_bytes(path, json.dumps(records, ensure_ascii=False).encode("utf-8"))


def _period_complete(index_path, refresh):
    return (
        not refresh
        and index_path.exists()
        and not (index_path.parent / "incomplete.json").exists()
    )


def _finish_period(index_path, records, unavailable):
    _write_index(index_path, records)
    marker = index_path.parent / "incomplete.json"
    if unavailable:
        save_bytes(marker, json.dumps({"unavailable_reports": unavailable}).encode())
    elif marker.exists():
        marker.unlink()


def _map_records(records, process, workers):
    """Process a bounded batch of records concurrently, preserving API order."""
    if workers == 1:
        for record in records:
            yield process(record)
        return
    records = iter(records)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        while True:
            batch = list(islice(records, workers * 4))
            if not batch:
                break
            yield from executor.map(process, batch)


def download_members(output, refresh):
    refresh = True  # Reference data can change without a new archive directory.
    records = list(
        pages("members", {}, output / "archive" / "members" / "pages", refresh)
    )
    save_bytes(
        output / "archive" / "members" / "members.json",
        json.dumps(records, ensure_ascii=False).encode("utf-8"),
    )
    members = [Member(**record["member"]).serialize() for record in records]
    save_bytes(
        output / "members" / "members.json",
        json.dumps(members, ensure_ascii=False).encode("utf-8"),
    )
    LOG.info("Saved %s member records", len(records))


def download_debates(output, start, end, refresh, metadata_only, workers=1):
    count = 0
    unavailable = 0
    skipped_periods = 0
    for first, last in month_ranges(start, end):
        refresh_period = refresh or last >= dt.date.today().replace(day=1)
        month_dir = month_directory(output, "debates", first, last)
        index_path = month_dir / "index.json"
        if _period_complete(index_path, refresh_period):
            skipped_periods += 1
            continue
        report_state = ReportFetchState()
        params = {"date_start": first.isoformat(), "date_end": last.isoformat()}

        def process(item):
            record = item.get("debateRecord", {})
            formats = record.get("formats") or {}
            entry = {
                "date": item.get("contextDate"),
                "uri": record.get("uri"),
                "files": {},
            }
            skipped_total = 0
            if not metadata_only:
                entry["files"], skipped = _save_linked_files(
                    formats, month_dir, "reports", refresh, entry["date"], report_state
                )
                skipped_total += skipped
                entry["sections"] = []
                for section_item in record.get("debateSections") or []:
                    section = section_item.get("debateSection") or {}
                    section_formats = section.get("formats") or {}
                    if "xml" in entry["files"] and isinstance(section_formats, dict):
                        # The full debate XML already contains its sections.
                        section_formats = {
                            kind: value
                            for kind, value in section_formats.items()
                            if kind != "xml"
                        }
                    section_files, skipped = _save_linked_files(
                        section_formats,
                        month_dir,
                        "reports/sections",
                        refresh,
                        section.get("debateSectionId") or entry["date"],
                        report_state,
                    )
                    skipped_total += skipped
                    entry["sections"].append(
                        {"id": section.get("debateSectionId"), "files": section_files}
                    )
            return entry, skipped_total

        index = []
        period_unavailable = 0
        for entry, skipped in _map_records(
            pages("debates", params, month_dir / "pages", refresh_period),
            process,
            workers,
        ):
            index.append(entry)
            count += 1
            unavailable += skipped
            period_unavailable += skipped
        _finish_period(index_path, index, period_unavailable)
        LOG.info("Completed %s", first.strftime("%Y-%m"))
    LOG.info(
        "Processed %s debate records; reused %s completed periods",
        count,
        skipped_periods,
    )
    if unavailable:
        LOG.warning(
            "Skipped %s unavailable report files; rerun to retry them", unavailable
        )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(OIREACHTAS_DIR))
    parser.add_argument(
        "--refresh", action="store_true", help="Re-fetch existing pages and reports"
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--collections", nargs="+", choices=COLLECTIONS, default=COLLECTIONS
    )
    args = parser.parse_args(argv)
    if args.workers < 1:
        parser.error("--workers must be at least 1")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    LOG.info("Saving data under %s", args.output_dir.resolve())
    selected = set(args.collections)
    if "members" in selected:
        download_members(args.output_dir, args.refresh)
    if "debates" in selected:
        download_debates(
            args.output_dir, FIRST_DEBATE, dt.date.today(), args.refresh, False,
            workers=args.workers,
        )


if __name__ == "__main__":
    main()
