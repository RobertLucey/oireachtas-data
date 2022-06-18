# Can use debate_Dáil Éireann_2012-06-06.pdf.txt for testing

import os
import datetime

from unittest import TestCase

from oireachtas_data.models.old_pdf import (
    PDF,
    Section
)


class OldPDFTest(TestCase):

    def setUp(self):
        self.resources_path = os.path.join(
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(
                        os.path.abspath(__file__)
                    )
                )
            ),
            'test/resources/pdfs'
        )

        self.de_2012_06_06 = os.path.join(
            self.resources_path,
            'debate_Dáil Éireann_2012-06-06.pdf'
        )

    def test_load(self):
        pdf = PDF(self.de_2012_06_06)
        pdf.load()

        self.assertTrue(pdf.loaded)

        text_possibles = [p.text.replace('\xa0', ' ') for p in pdf.possibles]

        self.assertTrue('Message from Select Sub-Committee' in text_possibles)
        self.assertEqual(
            pdf.matching_header('Message from Select Sub-Committee').lower(),
            'Message from Select Sub-Committee'.lower()
        )

        select_sub = [s for s in pdf.debate_sections if s.title.lower() == 'Message from Select Sub-Committee'.lower()][0]

        self.assertEqual(
            select_sub.speeches[0].serialize(),
            {
                'by': 'An Leas-Cheann Comhairle',
                'as': None,
                'eid': None,
                'paras': [
                    {
                        'title': None,
                        'eid': None,
                        'content': 'The Select sub-Committee on Jobs, Enterprise and Innovation has completed its consideration of the Credit Guarantee Bill 2012 and has made amendments thereto.'
                    }
                ]
            }
        )
