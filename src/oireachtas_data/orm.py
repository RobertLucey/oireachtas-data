"""Lazy, ORM-style objects backed by the downloaded Oireachtas archive."""

import datetime
import json
from functools import cached_property, lru_cache
from itertools import islice
from pathlib import Path
from urllib.parse import unquote

from oireachtas_data.constants import OIREACHTAS_DIR
from oireachtas_data.models.member import Member


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


class ArchiveModel:
    def __repr__(self):
        label = (
            getattr(self, "title", None)
            or getattr(self, "name", None)
            or getattr(self, "text", None)
            or getattr(self, "uri", None)
        )
        if isinstance(label, str) and len(label) > 80:
            label = label[:77] + "..."
        return "{}({!r})".format(type(self).__name__, label)

    @property
    def datetime(self):
        return datetime.datetime.strptime(self.date, '%Y-%m-%d')



class Document(ArchiveModel):
    """A document and its locally downloaded XML or PDF files."""

    def __init__(self, metadata=None, index=None, directory=None):
        self.metadata = metadata or {}
        self.uri = self.metadata.get("uri")
        self.title = self.metadata.get("showAs")
        self.date = self.metadata.get("date")
        self.language = self.metadata.get("lang")
        files = (index or {}).get("files") or {}
        self.files = {kind: Path(directory) / path for kind, path in files.items()}

    @property
    def xml(self):
        return self.files.get("xml")

    @property
    def pdf(self):
        return self.files.get("pdf") or self.files.get("writtens_pdf")


class MemberReference(ArchiveModel):
    """A member link in a question, vote, or bill."""

    def __init__(self, metadata, archive):
        self.metadata = metadata or {}
        self.uri = self.metadata.get("uri")
        self.name = self.metadata.get("showAs")
        self.member_code = self.metadata.get("memberCode") or (
            unquote(self.uri.rsplit("/", 1)[-1]) if self.uri else None
        )
        self._archive = archive

    @cached_property
    def member(self):
        return self._archive.member_by_code(self.member_code) if self.member_code else None


class EntityReference(ArchiveModel):
    def __init__(self, metadata):
        self.metadata = metadata or {}
        self.uri = self.metadata.get("uri")
        self.name = self.metadata.get("showAs")


class Question(ArchiveModel):
    def __init__(self, metadata, index, directory, archive):
        self.metadata = metadata
        data = metadata.get("question") or {}
        self.uri = data.get("uri")
        self.date = data.get("date") or metadata.get("contextDate")
        self.number = data.get("questionNumber")
        self.text = data.get("showAs")
        self.answer_text = data.get("answerText")
        self.question_type = data.get("questionType")
        self.by = MemberReference(data.get("by"), archive)
        self.to = EntityReference(data.get("to"))
        self.report = Document(data.get("debateSection"), index, directory)


class Vote(ArchiveModel):
    def __init__(self, metadata, index, directory, archive):
        self.metadata = metadata
        data = metadata.get("division") or {}
        self.uri = data.get("uri")
        self.date = data.get("date") or metadata.get("contextDate")
        self.outcome = data.get("outcome")
        self.subject = EntityReference(data.get("subject"))
        self.tallies = data.get("tallies") or {}
        self.debate_report = Document(data.get("debate"), index, directory)
        self._archive = archive

    def _members(self, kind):
        tally = self.tallies.get(kind) or {}
        return [
            MemberReference(item.get("member"), self._archive)
            for item in tally.get("members") or []
        ]

    @property
    def ta_members(self):
        return self._members("taVotes")

    @property
    def nil_members(self):
        return self._members("nilVotes")

    @property
    def staon_members(self):
        return self._members("staonVotes")


class Sponsor(ArchiveModel):
    def __init__(self, metadata, archive):
        self.metadata = metadata
        self.by = MemberReference(metadata.get("by"), archive)
        self.uri = self.by.uri
        self.name = self.by.name
        self.is_primary = metadata.get("isPrimary")

    @property
    def member(self):
        return self.by.member


class Act(ArchiveModel):
    def __init__(self, metadata):
        self.metadata = metadata
        self.uri = metadata.get("uri")
        self.year = metadata.get("actYear")
        self.number = metadata.get("actNo")
        self.title = metadata.get("shortTitleEn")
        self.date_signed = metadata.get("dateSigned")
        self.statutebook_uri = metadata.get("statutebookURI")


def _documents(data, index, group, wrapper, directory):
    metadata_items = data.get(group) or []
    index_items = index.get(group) or []
    if len(metadata_items) != len(index_items):
        raise ValueError("Archive metadata and document index disagree: " + group)
    return [
        Document(item.get(wrapper), saved, directory)
        for item, saved in zip(metadata_items, index_items)
    ]


class Bill(ArchiveModel):
    def __init__(self, metadata, index, directory, archive):
        self.metadata = metadata
        data = metadata.get("bill") or {}
        self.uri = data.get("uri")
        year = data.get("billYear")
        self.year = int(year) if year and str(year).isdigit() else year
        self.number = data.get("billNo")
        self.title = data.get("shortTitleEn")
        self.title_ga = data.get("shortTitleGa")
        self.status = data.get("status")
        self.act = Act(data["act"]) if isinstance(data.get("act"), dict) else None
        self.sponsors = [
            Sponsor(item.get("sponsor") or {}, archive)
            for item in data.get("sponsors") or []
        ]
        self.versions = _documents(data, index, "versions", "version", directory)
        self.related_docs = _documents(
            data, index, "relatedDocs", "relatedDoc", directory
        )
        self.amendment_lists = _documents(
            data, index, "amendmentLists", "amendmentList", directory
        )


class House(ArchiveModel):
    def __init__(self, metadata):
        self.metadata = metadata
        data = metadata.get("house") or {}
        self.uri = data.get("uri")
        self.name = data.get("showAs")
        self.code = data.get("houseCode")
        self.number = data.get("houseNo")
        self.seats = data.get("seats")
        self.date_range = data.get("dateRange")


@lru_cache(maxsize=256)
def _house_by_uri(archive, uri):
    return archive.houses.filter(uri=uri).first()


def _resolve_house(stub, archive):
    """Look up the full house record for an embedded house stub.

    Party and constituency records only embed a partial house reference
    (uri/code/showAs); seats and date_range live on the canonical record
    in the houses collection, keyed by the same uri. There are only ever a
    few dozen houses (Dáil/Seanad sittings) in total, so caching by uri
    avoids re-reading and re-scanning houses.json for every one of the
    hundreds of party/constituency records that reference the same handful
    of houses.
    """
    uri = stub.get("uri")
    if archive is not None and uri:
        match = _house_by_uri(archive, uri)
        if match is not None:
            return match
    return House({"house": stub})


class Party(ArchiveModel):
    def __init__(self, metadata, archive=None):
        self.metadata = metadata
        data = metadata.get("party") or {}
        self.uri = data.get("uri")
        self.name = data.get("showAs")
        self.code = data.get("partyCode")
        self._house_stub = metadata.get("house") or {}
        self._archive = archive

    @cached_property
    def house(self):
        return _resolve_house(self._house_stub, self._archive)


class Constituency(ArchiveModel):
    def __init__(self, metadata, archive=None):
        self.metadata = metadata
        data = metadata.get("constituencyOrPanel") or {}
        self.uri = data.get("uri")
        self.name = data.get("showAs")
        self.code = data.get("representCode")
        self.kind = data.get("representType")
        self._house_stub = metadata.get("house") or {}
        self._archive = archive

    @cached_property
    def house(self):
        return _resolve_house(self._house_stub, self._archive)


class ArchiveQuery:
    """Iterable query that reads one archive page at a time."""

    def __init__(self, archive, collection, filters=None):
        self.archive = archive
        self.collection = collection
        self.filters = filters or {}

    def all(self):
        return self

    def filter(self, **fields):
        return ArchiveQuery(self.archive, self.collection, dict(self.filters, **fields))

    def first(self):
        return next(iter(self), None)

    def get(self, **fields):
        matches = islice(self.filter(**fields), 2)
        first = next(matches, None)
        if first is None:
            raise LookupError("No {} record matches {}".format(self.collection, fields))
        if next(matches, None) is not None:
            raise LookupError(
                "Multiple {} records match {}".format(self.collection, fields)
            )
        return first

    def count(self):
        if self.filters:
            return sum(1 for _ in self)
        if self.collection in ("members", "houses", "parties", "constituencies"):
            path = self.archive.root / self.collection / (self.collection + ".json")
            return len(_read_json(path)) if path.exists() else 0
        seen = set()
        for path in self._indexes():
            for position, entry in enumerate(_read_json(path)):
                seen.add(entry.get("uri") or (str(path), position))
        return len(seen)

    def __getitem__(self, position):
        if not isinstance(position, int) or position < 0:
            raise IndexError(position)
        item = next(islice(self, position, position + 1), None)
        if item is None:
            raise IndexError(position)
        return item

    def __iter__(self):
        if self.collection in ("members", "houses", "parties", "constituencies"):
            path = self.archive.root / self.collection / (self.collection + ".json")
            if not path.exists():
                return
            for metadata in _read_json(path):
                item = self._make(metadata, {}, path.parent)
                if self._matches(item):
                    yield item
            return

        seen = set()
        for index_path in sorted(
            self._indexes(), key=self._index_sort_key, reverse=True
        ):
            index = _read_json(index_path)
            position = 0
            for page_path in sorted((index_path.parent / "pages").glob("*.json")):
                for metadata in _read_json(page_path)["results"]:
                    if position >= len(index):
                        raise ValueError(
                            "Archive index and pages disagree: " + str(index_path)
                        )
                    entry = index[position]
                    position += 1
                    key = entry.get("uri") or (str(index_path), position)
                    if key in seen:
                        continue
                    seen.add(key)
                    item = self._make(metadata, entry, index_path.parent)
                    if self._matches(item):
                        yield item
            if position != len(index):
                raise ValueError("Archive index and pages disagree: " + str(index_path))

    def _indexes(self):
        directory = self.archive.root / self.collection
        date = self.filters.get("date")
        year = self.filters.get("year")
        if self.collection in ("questions", "debates"):
            month = str(date)[:7] if date else "*"
            return sorted(directory.glob(month + "/*/index.json"))
        if self.collection == "votes":
            year = str(date)[:4] if date else "*"
        elif self.collection == "legislation":
            year = str(year) if year else "*"
        return sorted(directory.glob(str(year) + "/index.json"))

    @staticmethod
    def _index_sort_key(path):
        name = path.parent.name
        if "_" not in name:
            return (name, name, 0)
        start, end = name.split("_", 1)
        # Later end dates win; for the same end date, prefer the wider range.
        return (path.parent.parent.name, end, -int(start.replace("-", "")))

    def _make(self, metadata, index, directory):
        collection = self.collection
        if collection == "members":
            return Member(**metadata["member"])
        if collection == "debates":
            from oireachtas_data.archive import debate_from_record

            files = {
                kind: directory / path
                for kind, path in (index.get("files") or {}).items()
            }
            return debate_from_record(metadata, files, lazy=True)
        if collection == "questions":
            return Question(metadata, index, directory, self.archive)
        if collection == "votes":
            return Vote(metadata, index, directory, self.archive)
        if collection == "legislation":
            return Bill(metadata, index, directory, self.archive)
        if collection == "houses":
            return House(metadata)
        return {
            "parties": Party,
            "constituencies": Constituency,
        }[collection](metadata, self.archive)

    _LOOKUPS = ("contains", "in")

    def _matches(self, item):
        for field, value in self.filters.items():
            parts = field.split("__")
            lookup = None
            if len(parts) > 1 and parts[-1] in self._LOOKUPS:
                lookup = parts.pop()
            actual = item
            for part in parts:
                if actual is None:
                    break
                actual = getattr(actual, part, None)
            if lookup == "contains":
                if actual is None or value not in actual:
                    return False
            elif lookup == "in":
                if actual not in value:
                    return False
            elif actual != value:
                return False
        return True


class OireachtasArchive:
    """Entry point for querying locally downloaded Oireachtas records."""

    def __init__(self, archive_dir=None):
        self.root = (
            Path(archive_dir) if archive_dir else Path(OIREACHTAS_DIR) / "archive"
        )
        self._member_cache = {}
        self.members = ArchiveQuery(self, "members")
        self.houses = ArchiveQuery(self, "houses")
        self.parties = ArchiveQuery(self, "parties")
        self.constituencies = ArchiveQuery(self, "constituencies")
        self.questions = ArchiveQuery(self, "questions")
        self.votes = ArchiveQuery(self, "votes")
        self.bills = ArchiveQuery(self, "legislation")
        self.debates = ArchiveQuery(self, "debates")

    @cached_property
    def _member_rows(self):
        path = self.root / "members" / "members.json"
        if not path.exists():
            return {}
        return {
            row["member"].get("memberCode"): row["member"]
            for row in _read_json(path)
            if isinstance(row.get("member"), dict) and row["member"].get("memberCode")
        }

    def member_by_code(self, code):
        if code not in self._member_cache:
            row = self._member_rows.get(code)
            self._member_cache[code] = Member(**row) if row is not None else None
        return self._member_cache[code]

    def speeches_by(self, member, **filters):
        """Yield (debate, section, speech) for every speech by a member.

        Scans debates one at a time (each debate's XML is parsed and
        discarded as iteration moves on, so memory stays bounded regardless
        of archive size). Pass date="YYYY-MM-DD" or date__contains="YYYY-MM"
        filters, as supported by ``debates.filter(...)``, to narrow the scan
        when the full history isn't needed.
        """
        code = getattr(member, "member_code", member)
        for debate in self.debates.filter(**filters):
            for section in debate.debate_sections:
                for speech in section.speeches:
                    if speech.member_code == code:
                        yield debate, section, speech
