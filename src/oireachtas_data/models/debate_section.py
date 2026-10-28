"""A section of a downloaded debate."""

from oireachtas_data.models.speech import Speech


class DebateSection:
    __slots__ = (
        "bill",
        "contains_debate",
        "counts",
        "debate_section_id",
        "debate_type",
        "data_uri",
        "parent_debate_section",
        "show_as",
        "speakers",
        "speeches",
        "summaries",
        "content_items",
        "pdf_location",
    )

    def __init__(
        self,
        bill=None,
        contains_debate=None,
        counts=None,
        debate_section_id=None,
        debate_type=None,
        data_uri=None,
        parent_debate_section=None,
        show_as=None,
        speakers=None,
        speeches=None,
        summaries=None,
        content_items=None,
        pdf_location=None,
    ):
        self.bill = bill
        self.contains_debate = contains_debate
        self.counts = counts
        self.debate_section_id = debate_section_id
        self.debate_type = debate_type
        self.data_uri = data_uri
        self.parent_debate_section = parent_debate_section
        self.show_as = (show_as or "").strip()
        self.speakers = speakers if speakers is not None else []
        self.speeches = speeches if speeches is not None else []
        self.summaries = summaries if summaries is not None else []
        self.content_items = (
            content_items if content_items is not None else self.summaries + self.speeches
        )
        self.pdf_location = pdf_location

    def serialize(self):
        return {
            "bill": self.bill,
            "contains_debate": self.contains_debate,
            "counts": self.counts,
            "debate_section_id": self.debate_section_id,
            "debate_type": self.debate_type,
            "data_uri": self.data_uri,
            "parent_debate_section": self.parent_debate_section,
            "show_as": self.show_as,
            "speakers": self.speakers,
            "speeches": [speech.serialize() for speech in self.speeches],
            "summaries": [summary.serialize() for summary in self.summaries],
        }

    def speech_contains(self, substr, case_sensitive=True):
        content = "\n".join(speech.content for speech in self.speeches)
        if not case_sensitive:
            return substr.lower() in content.lower()
        return substr in content

    @property
    def content(self):
        parts = []
        for item in self.content_items:
            if isinstance(item, Speech):
                content = item.content.strip()
                if content:
                    parts.append((str(item.by) + ": " if item.by else "") + content)
            elif item.content:
                parts.append(item.content)
        return "\n".join(parts)

    @property
    def is_empty(self):
        return not self.speakers and not self.speeches and not self.summaries

    @property
    def computed_speakers(self):
        return {speech.by for speech in self.speeches}
