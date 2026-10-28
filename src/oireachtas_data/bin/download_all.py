"""Download Oireachtas member records and debate reports."""

import argparse
import datetime as dt
import hashlib
import json
import logging
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from oireachtas_data.constants import OIREACHTAS_DIR
from oireachtas_data.models.member import Member


API_URL = "https://api.oireachtas.ie/v1"
PAGE_SIZE = 1000
FIRST_DEBATE = dt.date(1919, 1, 1)
LOG = logging.getLogger("download_all")


def fetch(url):
    """Fetch a URL, retrying temporary API and network failures."""
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
    temporary = path.with_name(path.name + ".part")
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
            break
        skip += PAGE_SIZE


def month_ranges(start, end):
    cursor = start.replace(day=1)
    while cursor <= end:
        next_month = (cursor + dt.timedelta(days=32)).replace(day=1)
        yield max(cursor, start), min(next_month - dt.timedelta(days=1), end)
        cursor = next_month


def download_report_file(url, directory, kind, refresh):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname != "data.oireachtas.ie":
        raise ValueError("Unexpected report URL: " + url)
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    path = directory / (kind + "-" + digest + (".xml" if kind == "xml" else ".pdf"))
    if not path.exists() or refresh:
        try:
            save_bytes(path, fetch(url))
        except HTTPError as exc:
            if exc.code in (403, 404, 410) and path.exists():
                LOG.warning(
                    "Could not refresh %s (%s); keeping saved file", url, exc.code
                )
            else:
                raise
    return path


def download_members(output, refresh):
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


def download_debates(output, start, end, refresh, metadata_only):
    count = 0
    unavailable = 0
    for first, last in month_ranges(start, end):
        month_dir = (
            output
            / "archive"
            / "debates"
            / first.strftime("%Y-%m")
            / (first.isoformat() + "_" + last.isoformat())
        )
        params = {"date_start": first.isoformat(), "date_end": last.isoformat()}
        index = []
        for item in pages("debates", params, month_dir / "pages", refresh):
            count += 1
            record = item.get("debateRecord", {})
            formats = record.get("formats") or {}
            entry = {
                "date": item.get("contextDate"),
                "uri": record.get("uri"),
                "files": {},
            }
            if not metadata_only:
                for kind in ("xml", "pdf", "writtens_pdf"):
                    format_data = formats.get(kind) or {}
                    url = format_data.get("uri")
                    if url:
                        try:
                            path = download_report_file(
                                url, month_dir / "reports", kind, refresh
                            )
                        except HTTPError as exc:
                            if exc.code not in (403, 404, 410):
                                raise
                            unavailable += 1
                            LOG.warning(
                                "Skipping unavailable %s report for %s (%s): %s",
                                kind,
                                entry["date"],
                                exc.code,
                                url,
                            )
                        else:
                            entry["files"][kind] = str(path.relative_to(month_dir))
            index.append(entry)
        save_bytes(
            month_dir / "index.json",
            json.dumps(index, ensure_ascii=False).encode("utf-8"),
        )
        LOG.info("Completed %s", first.strftime("%Y-%m"))
    LOG.info("Processed %s debate records", count)
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
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    LOG.info("Saving data under %s", args.output_dir.resolve())
    download_members(args.output_dir, args.refresh)
    download_debates(
        args.output_dir, FIRST_DEBATE, dt.date.today(), args.refresh, False
    )


if __name__ == "__main__":
    main()
