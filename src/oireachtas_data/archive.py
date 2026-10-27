"""Read debate records and report files saved by oireachtas_download."""

import json
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree

from oireachtas_data.constants import OIREACHTAS_DIR
from oireachtas_data.models.debate import Debate
from oireachtas_data.models.debate_section import DebateSection
from oireachtas_data.models.para import Para
from oireachtas_data.models.speech import Speech


def _name(element):
    return element.tag.rsplit("}", 1)[-1]


def _speech(element):
    paragraphs = [
        Para(
            title=paragraph.get("title"),
            eid=paragraph.get("eId") or paragraph.get("eid"),
            content="".join(paragraph.itertext()),
        )
        for paragraph in element.iter()
        if _name(paragraph) == "p"
    ]
    return Speech(
        by=element.get("by"),
        _as=element.get("as"),
        eid=element.get("eId") or element.get("eid"),
        paras=paragraphs,
    )


def _section(metadata, element, speeches, pdf_path):
    formats = metadata.get("formats") or {}
    xml_format = formats.get("xml") or {}
    heading = (
        next((child for child in element if _name(child) == "heading"), None)
        if element is not None
        else None
    )
    show_as = metadata.get("showAs") or (
        "".join(heading.itertext()) if heading is not None else "Untitled"
    )
    section_id = metadata.get("debateSectionId") or (
        element.get("eId") if element is not None else None
    )
    return DebateSection(
        bill=metadata.get("bill"),
        contains_debate=metadata.get("containsDebate"),
        counts=metadata.get("counts"),
        debate_section_id=section_id,
        debate_type=metadata.get("debateType"),
        data_uri=xml_format.get("uri"),
        parent_debate_section=metadata.get("parentDebateSection"),
        show_as=show_as,
        speakers=metadata.get("speakers") or [],
        speeches=speeches,
        pdf_location=pdf_path,
        loaded=True,
    )


class DownloadedDebate(Debate):
    __slots__ = ("metadata", "files", "uri", "_text")

    def __init__(self, metadata, files):
        self.metadata = metadata
        record = metadata.get("debateRecord") or {}
        self.uri = record.get("uri")
        self.files = files
        xml_path = files.get("xml")
        root = ElementTree.parse(xml_path).getroot() if xml_path is not None else None
        self._text = " ".join(root.itertext()) if root is not None else None

        xml_sections = {}
        section_order = []
        speeches_by_section = defaultdict(list)
        unsectioned_speeches = []
        if root is not None:
            parents = {child: parent for parent in root.iter() for child in parent}
            for element in root.iter():
                if _name(element) == "debateSection":
                    xml_sections[element.get("eId") or element.get("eid")] = element
                    section_order.append(element)
                elif _name(element) == "speech":
                    parent = parents.get(element)
                    while parent is not None and _name(parent) != "debateSection":
                        parent = parents.get(parent)
                    if parent is not None:
                        speeches_by_section[parent].append(_speech(element))
                    else:
                        unsectioned_speeches.append(_speech(element))

        sections = []
        used_xml_sections = set()
        pdf_path = files.get("pdf") or files.get("writtens_pdf")
        for item in record.get("debateSections") or []:
            section_metadata = item.get("debateSection") or {}
            element = xml_sections.get(section_metadata.get("debateSectionId"))
            if element is not None:
                used_xml_sections.add(element)
            sections.append(
                _section(section_metadata, element, speeches_by_section.get(element, []), pdf_path)
            )
        for element in section_order:
            if element not in used_xml_sections:
                sections.append(
                    _section({}, element, speeches_by_section.get(element, []), pdf_path)
                )
        if unsectioned_speeches:
            sections.append(
                _section({"showAs": "Unsectioned"}, None, unsectioned_speeches, pdf_path)
            )

        formats = record.get("formats") or {}
        xml_format = formats.get("xml") or {}
        super().__init__(
            date=metadata.get("contextDate") or record.get("date"),
            chamber=(record.get("chamber") or {}).get("showAs"),
            counts=record.get("counts"),
            debate_sections=sections,
            debate_type=record.get("debateType"),
            data_uri=xml_format.get("uri"),
            loaded=True,
        )

    @property
    def text(self):
        """Plain text from the downloaded report XML, when one is available."""
        return self._text

    @property
    def pdf_location(self):
        return self.files.get("pdf") or self.files.get("writtens_pdf")


class DownloadedDebates:
    """List-like archive that loads a metadata page only when accessed."""

    def __init__(self, archive_dir=None):
        root = Path(archive_dir) if archive_dir else Path(OIREACHTAS_DIR) / "archive"
        self._entries = []
        seen = set()
        for index_path in sorted((root / "debates").glob("*/*/index.json")):
            directory = index_path.parent
            index = json.loads(index_path.read_text(encoding="utf-8"))
            page_paths = sorted((directory / "pages").glob("*.json"))
            if len(page_paths) != len(index) // 1000 + 1:
                raise ValueError("Archive index and pages disagree: " + str(directory))
            for position, entry in enumerate(index):
                key = entry.get("uri") or (str(index_path), position)
                if key in seen:
                    continue
                seen.add(key)
                files = {kind: directory / path for kind, path in entry["files"].items()}
                self._entries.append((page_paths[position // 1000], position % 1000, files))

    @lru_cache(maxsize=1)
    def _page(self, path):
        return json.loads(path.read_text(encoding="utf-8"))["results"]

    def __len__(self):
        return len(self._entries)

    def __getitem__(self, position):
        if isinstance(position, slice):
            return [self[i] for i in range(*position.indices(len(self)))]
        return self._item(position)

    @lru_cache(maxsize=16)
    def _item(self, position):
        page_path, offset, files = self._entries[position]
        return DownloadedDebate(self._page(page_path)[offset], files)

    def __iter__(self):
        for position in range(len(self)):
            yield self[position]


def get_downloaded_debates(archive_dir=None):
    """Load all archived debates into a list."""
    return list(DownloadedDebates(archive_dir))
