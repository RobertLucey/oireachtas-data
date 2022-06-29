import os
import datetime
import json
import requests
from collections import defaultdict

from oireachtas_data.constants import DEBATES_DIR
from oireachtas_data.models.debate_section import DebateSection


class Debate():

    __slots__ = (
        'date',
        'chamber',
        'counts',
        'debate_sections',
        'debate_type',
        'data_uri',
        'loaded',
        '_json_location'
    )

    def __init__(
        self,
        date=None,
        chamber=None,
        counts=None,
        debate_sections=None,
        debate_type=None,
        data_uri=None,
        loaded=False
    ):
        '''

        :kwarg date: The date of the debate in YYYY-MM-DD format
        :kwarg chamber: Dail or Seanad
        :kwarg counts:
        :kwarg debate_sections: list of debate sections in json from the api
        :kwarg debate_type: the tye of the debate, usually just 'debate'
        :kwarg data_uri:
        '''
        self.date = date
        self.chamber = chamber
        self.counts = counts
        self.debate_sections = debate_sections
        self.debate_type = debate_type
        self.data_uri = data_uri

        self.loaded = loaded

        self._json_location = None

    def set_filepath(self, filepath):
        self._json_location = filepath

    @staticmethod
    def from_file(filepath):
        from oireachtas_data.utils import get_file_content
        debate = Debate()
        debate.set_filepath(filepath)
        return debate

    @staticmethod
    def parse(data):
        return Debate(
            date=data['date'],
            chamber=data['chamber'],
            counts=data['counts'],
            debate_sections=[
                DebateSection.parse(d) for d in data['sections']
            ],
            debate_type=data['debate_type'],
            data_uri=data['data_uri'],
            loaded=True
        )

    def load_data(self):
        '''
        Load data from the data_uri to populate the debate sections
        '''
        if self.loaded:
            return

        if os.path.exists(self.json_location):
            from oireachtas_data.utils import get_file_content
            data = get_file_content(self.json_location)
            self.date = data['date']
            self.chamber = data['chamber']
            self.counts = data['counts']
            self.debate_sections = [
                DebateSection.parse(d) for d in data['sections']
            ]
            self.debate_type = data['debate_type']
            self.data_uri = data['data_uri']
        else:

            chambers = {
                'Dáil Éireann': 'dail',
                'Seanad Éireann': 'seanad'
            }
            url = 'https://data.oireachtas.ie/ie/oireachtas/debateRecord/%s/%s/debate/mul@/main.pdf' % (
                chambers[self.chamber],
                self.date
            )

            pdf_request = requests.get(url, stream=True)

            # not self.pdf_location as recursive error
            pdf_location = os.path.join(
                DEBATES_DIR,
                '%s_%s_%s.pdf' % ('debate', self.chamber, self.date)
            )

            with open(pdf_location, 'wb') as pdfile:
                for chunk in pdf_request.iter_content(2000):
                    pdfile.write(chunk)

            # If we're missing data from the api cause of being forbidden we can get some data from the pdf

            debate_sections = []
            for idx, section in enumerate(self.debate_sections):
                raw_debate_section = section['debateSection']
                debate_section = DebateSection(
                    bill=raw_debate_section['bill'],
                    contains_debate=raw_debate_section['containsDebate'],
                    counts=raw_debate_section['counts'],
                    debate_section_id=raw_debate_section['debateSectionId'],
                    debate_type=raw_debate_section['debateType'],
                    data_uri=raw_debate_section['formats']['xml']['uri'],
                    parent_debate_section=raw_debate_section['parentDebateSection'],
                    show_as=raw_debate_section['showAs'],
                    show_as_idx=idx,
                    show_as_context=[d['debateSection']['showAs'] for d in self.debate_sections],
                    speakers=raw_debate_section['speakers'],
                    pdf_location=pdf_location
                )
                debate_section.load_data()
                debate_sections.append(debate_section)

            self.debate_sections = debate_sections

        self.loaded = True

    def serialize(self):
        self.load_data()
        return {
            'date': self.date,
            'chamber': self.chamber,
            'counts': self.counts,
            'debate_type': self.debate_type,
            'data_uri': self.data_uri,
            'sections': [
                s.serialize() for s in self.debate_sections
            ]
        }

    def write(self):
        with open(self.json_location, 'w') as outfile:
            outfile.write(json.dumps(self.serialize()))

    @property
    def pdf_location(self):
        self.load_data()
        return os.path.join(
            DEBATES_DIR,
            '%s_%s_%s.pdf' % ('debate', self.chamber, self.date)
        )

    @property
    def json_location(self):
        if self._json_location:
            return self._json_location

        return os.path.join(
            DEBATES_DIR,
            '%s_%s_%s.json' % ('debate', self.chamber, self.date)
        )

    @property
    def content_by_speaker(self):
        self.load_data()
        speakers = defaultdict(list)
        for section in self.debate_sections:
            for speech in section.speeches:
                if speech.member_obj is not None:
                    speakers[speech.member_obj.pid].extend(speech.paras)
                else:
                    # Couldn't get pid but want to include anyway
                    speakers[speech.by].extend(speech.paras)
        return speakers

    @property
    def timestamp(self):
        self.load_data()
        return datetime.datetime.strptime(
            self.date,
            '%Y-%m-%d'
        )
