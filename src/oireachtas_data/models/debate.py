"""A debate loaded from the downloaded archive."""

import datetime
from collections import defaultdict


class Debate:
    __slots__ = (
        "date",
        "chamber",
        "counts",
        "debate_sections",
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
    ):
        self.date = date
        self.chamber = chamber
        self.counts = counts
        self.debate_sections = debate_sections if debate_sections is not None else []
        self.debate_type = debate_type
        self.data_uri = data_uri
        self.metadata = metadata if metadata is not None else {}
        self.files = files if files is not None else {}
        self.uri = uri
        self._text = text

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
