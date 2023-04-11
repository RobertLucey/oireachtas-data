import urllib
from urllib.request import urlopen

import bs4

from oireachtas_data.models.speech import Speech
from oireachtas_data.models.para import Para
from oireachtas_data.models.pdf import pdf_parser_get

from oireachtas_data import logger

pdf_cache = {}


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
        "show_as_idx",
        "show_as_context",
        "speakers",
        "speeches",
        "pdf_location",
        "loaded",
        "debate_sections_context",
        "debate_section_idx",
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
        show_as_idx=None,
        show_as_context=None,
        speakers=None,
        speeches=None,
        pdf_location=None,
        loaded=False,
        debate_sections_context=None,
        debate_section_idx=None,
    ):
        self.bill = bill
        self.contains_debate = contains_debate
        self.counts = counts
        self.debate_section_id = debate_section_id
        self.debate_type = debate_type
        self.data_uri = data_uri
        self.parent_debate_section = parent_debate_section
        self.show_as = show_as.strip()
        self.show_as_idx = show_as_idx
        self.show_as_context = show_as_context
        self.speakers = speakers
        self.speeches = speeches if speeches else []

        self.debate_sections_context = debate_sections_context
        self.debate_section_idx = debate_section_idx

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

    @property
    def pdf_obj(self):
        parser = pdf_parser_get(self.pdf_location)

        if parser is None:
            return None

        if self.pdf_location not in pdf_cache:
            pdf_cache[self.pdf_location] = parser(self.pdf_location)

        return pdf_cache[self.pdf_location]

    def load_data(self):
        """
        Load data from the data_uri to populate the speeches and
        their paragraphs
        """
        if self.loaded:
            return

        use_pdf = True

        try:
            source = urlopen(self.data_uri)
            use_pdf = False
        except (Exception, urllib.error.HTTPError) as ex:
            if str(ex) != "HTTP Error 403: Forbidden":
                raise ex
            else:
                pdf = self.pdf_obj

                # Need to know what occurace of the show_as is, since there can be multiples
                # will then need to get that one in the debate section

                # this self.show_as is the xth occurance
                # xth_occurance = self.show_as_context[0:self.show_as_idx + 1].count(self.show_as)
                # import pdb; pdb.set_trace()

                matching_header = pdf.matching_header(self.show_as)
                if matching_header is None:
                    # FIXME: may not be in debate sections, could just be on its own
                    # look if there's a line just containing the header
                    logger.warning(
                        f'Could not find "{self.show_as}" in {self.pdf_location}'
                    )
                else:
                    # TODO: as sections are used, remove them as there can be multples, don't want to repeat
                    # can update the model since it's shared

                    context = self.debate_sections_context
                    idx = self.debate_section_idx
                    pre_show_as = [c["debateSection"]["showAs"] for c in context[:idx]]
                    post_show_as = [c["debateSection"]["showAs"] for c in context[idx:]]

                    if (
                        matching_header in pre_show_as
                        and matching_header in post_show_as
                        and matching_header == context[idx]["debateSection"]["showAs"]
                    ):
                        # count which instance of this it is, then instead of getting the first, get the nth of that name
                        try:
                            section = [
                                s
                                for s in pdf.debate_sections
                                if s.title.lower().strip()
                                == matching_header.lower().strip()
                            ][pre_show_as.count(matching_header)]
                            self.speeches.extend(section.speeches)
                        except IndexError:
                            logger.warning(
                                'Could not get header "%s" from "%s"'
                                % (matching_header, pdf.fp)
                            )

                    else:
                        # Just get the first and carry on since it's the first time coming across
                        try:
                            section = [
                                s
                                for s in pdf.debate_sections
                                if s.title.lower().strip()
                                == matching_header.lower().strip()
                            ][0]
                            self.speeches.extend(section.speeches)
                        except IndexError:
                            logger.warning(
                                'Could not get header "%s" from "%s"'
                                % (matching_header, pdf.fp)
                            )

        else:
            soup = bs4.BeautifulSoup(source, "html.parser")

            # heading
            # soup.find('debatesection').find('heading').text

            for speech in soup.find("debatesection").find_all("speech"):
                paras = [
                    Para(
                        title=p.attrs.get("title", None),
                        eid=p.attrs.get("eid", None),
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

            # Could also get summary

            self.loaded = True

            if use_pdf:
                logger.debug(
                    'Needed to get pdf to parse "{self.show_as}": {self.pdf_location}'
                )

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
    def is_from_pdf(self):
        any_eid = [speech for speech in self.speeches if speech.eid] != []
        has_content = [speech for speech in self.speeches if speech.content] != []
        return any_eid and has_content

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
