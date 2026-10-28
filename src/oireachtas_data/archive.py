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


def _text(element):
    return " ".join("".join(element.itertext()).split())


def _summary(element):
    return Para(
        eid=element.get("eId") or element.get("eid"),
        content=_text(element),
    )


def _speech(element):
    paragraphs = [
        Para(
            title=paragraph.get("title"),
            eid=paragraph.get("eId") or paragraph.get("eid"),
            content=_text(paragraph),
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


def _section(metadata, element, speeches, summaries, content_items, pdf_path):
    formats = metadata.get("formats") or {}
    xml_format = formats.get("xml") or {}
    heading = (
        next((child for child in element if _name(child) == "heading"), None)
        if element is not None
        else None
    )
    show_as = metadata.get("showAs") or (
        _text(heading) if heading is not None else "Untitled"
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
        summaries=summaries,
        content_items=content_items,
        pdf_location=pdf_path,
    )


def debate_from_record(metadata, files):
    """Build the single Debate model from saved API metadata and report XML."""
    record = metadata.get("debateRecord") or {}
    xml_path = files.get("xml")
    root = ElementTree.parse(xml_path).getroot() if xml_path is not None else None
    text = _text(root) if root is not None else None

    xml_sections = {}
    section_order = []
    speeches_by_section = defaultdict(list)
    summaries_by_section = defaultdict(list)
    items_by_section = defaultdict(list)
    unsectioned_speeches = []
    unsectioned_summaries = []
    unsectioned_items = []
    if root is not None:
        parents = {child: parent for parent in root.iter() for child in parent}
        for element in root.iter():
            if _name(element) == "debateSection":
                xml_sections[element.get("eId") or element.get("eid")] = element
                section_order.append(element)
            elif _name(element) in ("speech", "summary"):
                parent = parents.get(element)
                while parent is not None and _name(parent) != "debateSection":
                    parent = parents.get(parent)
                item = _speech(element) if _name(element) == "speech" else _summary(element)
                if parent is not None:
                    if _name(element) == "speech":
                        speeches_by_section[parent].append(item)
                    else:
                        summaries_by_section[parent].append(item)
                    items_by_section[parent].append(item)
                else:
                    if _name(element) == "speech":
                        unsectioned_speeches.append(item)
                    else:
                        unsectioned_summaries.append(item)
                    unsectioned_items.append(item)

    sections = []
    used_xml_sections = set()
    pdf_path = files.get("pdf") or files.get("writtens_pdf")
    for item in record.get("debateSections") or []:
        section_metadata = item.get("debateSection") or {}
        element = xml_sections.get(section_metadata.get("debateSectionId"))
        if element is not None:
            used_xml_sections.add(element)
        sections.append(
            _section(
                section_metadata,
                element,
                speeches_by_section.get(element, []),
                summaries_by_section.get(element, []),
                items_by_section.get(element, []),
                pdf_path,
            )
        )
    for element in section_order:
        if element not in used_xml_sections:
            sections.append(
                _section(
                    {},
                    element,
                    speeches_by_section.get(element, []),
                    summaries_by_section.get(element, []),
                    items_by_section.get(element, []),
                    pdf_path,
                )
            )
    if unsectioned_items:
        sections.append(
            _section(
                {"showAs": "Unsectioned"},
                None,
                unsectioned_speeches,
                unsectioned_summaries,
                unsectioned_items,
                pdf_path,
            )
        )

    formats = record.get("formats") or {}
    xml_format = formats.get("xml") or {}
    return Debate(
        date=metadata.get("contextDate") or record.get("date"),
        chamber=(record.get("chamber") or {}).get("showAs"),
        counts=record.get("counts"),
        debate_sections=sections,
        debate_type=record.get("debateType"),
        data_uri=xml_format.get("uri"),
        metadata=metadata,
        files=files,
        uri=record.get("uri"),
        text=text,
    )


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
        return debate_from_record(self._page(page_path)[offset], files)

    def __iter__(self):
        for position in range(len(self)):
            yield self[position]


def get_downloaded_debates(archive_dir=None):
    """Load all archived debates into a list."""
    return list(DownloadedDebates(archive_dir))
