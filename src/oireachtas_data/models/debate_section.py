from urllib.request import urlopen

import bs4

from oireachtas_data.models.speech import Speech
from oireachtas_data.models.para import Para


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
        "pdf_location",
        "loaded",
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
        pdf_location=None,
        loaded=False,
    ):
        self.bill = bill
        self.contains_debate = contains_debate
        self.counts = counts
        self.debate_section_id = debate_section_id
        self.debate_type = debate_type
        self.data_uri = data_uri
        self.parent_debate_section = parent_debate_section
        self.show_as = show_as.strip()
        self.speakers = speakers
        self.speeches = speeches if speeches else []

        self.pdf_location = pdf_location
        self.loaded = loaded

    @staticmethod
    def parse(data):
        return DebateSection(
            bill=data["bill"],
            contains_debate=data["contains_debate"],
            counts=data["counts"],
            debate_section_id=data["debate_section_id"],
            debate_type=data["debate_type"],
            data_uri=data["data_uri"],
            parent_debate_section=data["parent_debate_section"],
            show_as=data["show_as"],
            speakers=data["speakers"],
            speeches=[Speech.parse(s) for s in data["speeches"]],
            loaded=True,
        )

    def get_data_from_uri(self, uri):
        return urlopen(uri)

    def load_data(self):
        """
        Load data from the data_uri to populate the speeches and
        their paragraphs
        """
        if self.loaded:
            return

        source = self.get_data_from_uri(self.data_uri)
        soup = bs4.BeautifulSoup(source, "html.parser")
        section = soup.find("debatesection")
        if section is None:
            raise ValueError("No debate section in " + str(self.data_uri))
        for speech in section.find_all("speech"):
            paras = [
                Para(
                    title=p.attrs.get("title"),
                    eid=p.attrs.get("eid"),
                    content=p.text,
                )
                for p in speech.find_all("p")
            ]
            self.speeches.append(
                Speech(
                    by=speech.attrs.get("by"),
                    _as=speech.attrs.get("as"),
                    eid=speech.attrs.get("eid"),
                    paras=paras,
                )
            )
        self.loaded = True

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
            "speeches": [s.serialize() for s in self.speeches],
        }

    def speech_contains(self, substr, case_sensitive=True):
        content = ""
        for speech in self.speeches:
            content += "\n" + speech.content

        if case_sensitive:
            return substr in content
        else:
            return substr.lower() in content.lower()

    @property
    def content(self):
        return "\n".join(
            ["\n" + speech.by + ": " + speech.content for speech in self.speeches]
        )

    @property
    def is_empty(self):
        # this can happen when there's access denied errors
        return self.speakers == [] and self.speeches == []

    @property
    def computed_speakers(self):
        speakers = set()
        for speech in self.speeches:
            speakers.add(speech.by)

        return speakers
