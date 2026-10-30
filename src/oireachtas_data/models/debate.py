"""A debate loaded from the downloaded archive."""

import datetime
from collections import defaultdict


class Debate:
    __slots__ = (
        "date",
        "chamber",
        "counts",
        "_debate_sections",
        "_sections_loader",
        "debate_type",
        "data_uri",
        "metadata",
        "files",
        "uri",
        "_text",
    )

    def __init__(
        self,
        date=None,
        chamber=None,
        counts=None,
        debate_sections=None,
        debate_type=None,
        data_uri=None,
        metadata=None,
        files=None,
        uri=None,
        text=None,
        sections_loader=None,
    ):
        self.date = date
        self.chamber = chamber
        self.counts = counts
        self._debate_sections = debate_sections
        self._sections_loader = sections_loader
        self.debate_type = debate_type
        self.data_uri = data_uri
        self.metadata = metadata if metadata is not None else {}
        self.files = files if files is not None else {}
        self.uri = uri
        self._text = text

    @property
    def debate_sections(self):
        if self._debate_sections is None:
            self._debate_sections = (
                self._sections_loader() if self._sections_loader is not None else []
            )
            self._sections_loader = None
        return self._debate_sections

    @debate_sections.setter
    def debate_sections(self, sections):
        self._debate_sections = sections
        self._sections_loader = None

    def serialize(self):
        return {
            "date": self.date,
            "chamber": self.chamber,
            "counts": self.counts,
            "debate_type": self.debate_type,
            "data_uri": self.data_uri,
            "sections": [section.serialize() for section in self.debate_sections],
        }

    @property
    def text(self):
        """The debate's full flattened text.

        Computing this walks every text node in the debate XML, which is
        expensive for long transcripts and is rarely needed (most callers
        only want specific sections/speeches). ``_text`` may hold the
        already-computed string, None, or a zero-arg callable to compute
        and cache it lazily on first access.
        """
        if callable(self._text):
            self._text = self._text()
        return self._text

    @property
    def pdf_location(self):
        return self.files.get("pdf") or self.files.get("writtens_pdf")

    @property
    def content_by_speaker(self):
        speakers = defaultdict(list)
        for section in self.debate_sections:
            for speech in section.speeches:
                member = speech.member_obj
                key = member.pid if member is not None else speech.by
                speakers[key].extend(speech.paras)
        return speakers

    @property
    def timestamp(self):
        return datetime.datetime.strptime(self.date, "%Y-%m-%d")
