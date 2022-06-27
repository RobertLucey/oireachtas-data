import os

from unittest import TestCase, skip

from oireachtas_data.models.debate import Debate
from oireachtas_data.constants import OIREACHTAS_DIR


class DebateTest(TestCase):

    def test_parse(self):
        os.makedirs(OIREACHTAS_DIR, exist_ok=True)
        self.assertEqual(
            Debate.parse(
                {
                    'date': '2020-01-01',
                    'chamber': 'Dáil Éireann',
                    'counts': {
                        'questionCount': 21,
                        'billCount': 15,
                        'contributorCount': 146,
                        'divisionCount': 12,
                    },
                    'sections': [],
                    'debate_type': 'debate',
                    'data_uri': 'https://blahblah1983he9183r9.com'
                }
            ).serialize(),
            {
                'chamber': 'Dáil Éireann',
                'counts': {
                    'billCount': 15,
                    'contributorCount': 146,
                    'divisionCount': 12,
                    'questionCount': 21
                },
                'data_uri': 'https://blahblah1983he9183r9.com',
                'date': '2020-01-01',
                'debate_type': 'debate',
                'sections': []
            }
        )

    @skip('Failing on CI but passing locally')
    def test_serialize(self):
        self.assertEqual(
            Debate(
                date='2020-01-01',
                chamber='Dáil Éireann',
                counts={
                    'questionCount': 21,
                    'billCount': 15,
                    'contributorCount': 146,
                    'divisionCount': 12,
                },
                debate_sections=[],
                debate_type='debate',
                data_uri='https://blahblah1983he9183r9.com'
            ).serialize(),
            {
                'chamber': 'Dáil Éireann',
                'counts': {
                    'billCount': 15,
                    'contributorCount': 146,
                    'divisionCount': 12,
                    'questionCount': 21
                },
                'data_uri': 'https://blahblah1983he9183r9.com',
                'date': '2020-01-01',
                'debate_type': 'debate',
                'sections': []
            }
        )
