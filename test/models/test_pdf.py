import os
import datetime

from unittest import TestCase

from oireachtas_data.models.pdf import (
    PDF,
    Section
)


class SectionTest(TestCase):

    def test_content_remove_dates(self):
        self.assertEqual(
            Section(data='HEADER �����������������������������������������������������������\nzero 00000\n123\none\n12/12/2021\n11111 two 22222 three 33333', title='one', next_title='two').content,
            '11111'
        )

    def test_content(self):
        self.assertEqual(
            Section(data='HEADER ����������������������������������������������������������� zero 00000 one 11111 two 22222 three 33333', title='one', next_title='two').content,
            '11111'
        )
        self.assertEqual(
            Section(data='HEADER ����������������������������������������������������������� zero 00000 one 11111 two 22222 three 33333', title='one', next_title=None).content,
            '11111 two 22222 three 33333'
        )

    def test_non_header_content(self):
        self.assertTrue(
            'zero 00000 one 11111 two 22222 three 33333' in Section(data='HEADER ����������������������������������������������������������� zero 00000 one 11111 two 22222 three 33333', title='one', next_title=None).non_header_content,
        )
        self.assertTrue(
            'HEADER' not in Section(data='HEADER ����������������������������������������������������������� zero 00000 one 11111 two 22222 three 33333', title='one', next_title=None).non_header_content,
        )

    def test_speeches(self):
        section = Section(
            data='''
HEADER
SOMETHING ����������������������������������������������������������� 123

zero

padding, time goes here

Me: Who likes short shorts?

You: I like short shorts!

one

Me: This should be ignored
            ''',
            title='zero',
            next_title='one'
        )

        self.assertEqual(len(section.speeches), 2)
        print(section.speeches[0].serialize())
        self.assertEqual(
            section.speeches[0].serialize(),
            {
                'as': None,
                'by': 'Me',
                'eid': None,
                'paras': [{'content': 'Who likes short shorts?', 'eid': None, 'title': None}]
            }
        )
        self.assertEqual(
            section.speeches[1].serialize(),
            {
                'as': None,
                'by': 'You',
                'eid': None,
                'paras': [{'content': 'I like short shorts!', 'eid': None, 'title': None}]
            }
        )


class PDFTest(TestCase):

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

    def test_section_headers(self):
        pdf_path = os.path.join(
            self.resources_path,
            'debate_Seanad Éireann_2021-11-18.pdf'
        )

        self.assertEqual(
            PDF(pdf_path).section_headers,
            [
                'Gnó an tSeanaid - Business of Seanad',
                'Nithe i dtosach suíonna - Commencement Matters',
                'School Enrolments',
                'National Asset Management Agency',
                'General Practitioner Services',
                'Equality Issues',
                'Gnó an tSeanaid - Business of Seanad',
                'An tOrd Gnó - Order of Business',
                'Address to Seanad Éireann by An Taoiseach',
                'Air Accident Investigation Unit Final Report into R116 Air Accident: Statements'
            ]
        )

    def test_debate_sections(self):
        pdf_path = os.path.join(
            self.resources_path,
            'debate_Seanad Éireann_2021-11-18.pdf'
        )

        pdf = PDF(pdf_path)
        self.assertEqual(len(pdf.debate_sections), 10)

    def test_date(self):
        pdf_path = os.path.join(
            self.resources_path,
            'debate_Seanad Éireann_2021-11-18.pdf'
        )

        pdf = PDF(pdf_path)
        self.assertEqual(pdf.date, datetime.datetime(2021, 11, 18, 0, 0))

    def test_load(self):
        pdf_path = os.path.join(
            self.resources_path,
            'debate_Seanad Éireann_2021-11-18.pdf'
        )

        pdf = PDF(pdf_path)
        pdf.load()
        self.assertGreater(len(pdf.data), 250_000)
