import os

from unittest import TestCase, skip

from oireachtas_data.models.debate_section import DebateSection


class DebateSectionTest(TestCase):
    def setUp(self):
        self.resources_path = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "test/resources/",
        )
        self.resources_pdf_path = os.path.join(self.resources_path, "pdfs")

    def test_parse(self):
        self.assertEqual(
            DebateSection.parse(
                {
                    "bill": None,
                    "contains_debate": True,
                    "counts": {"speakerCount": 1, "speechCount": 1},
                    "debate_section_id": "dbsect_11",
                    "debate_type": "debate",
                    "data_uri": "https://something123919230192.com",
                    "parent_debate_section": None,
                    "show_as": "something",
                    "speakers": [],
                    "speeches": [],
                    "loaded": False,
                }
            ).serialize(),
            {
                "bill": None,
                "contains_debate": True,
                "counts": {"speakerCount": 1, "speechCount": 1},
                "data_uri": "https://something123919230192.com",
                "debate_section_id": "dbsect_11",
                "debate_type": "debate",
                "parent_debate_section": None,
                "show_as": "something",
                "speakers": [],
                "speeches": [],
            },
        )

    def test_serialize(self):
        self.assertEqual(
            DebateSection(
                **{
                    "bill": None,
                    "contains_debate": True,
                    "counts": {"speakerCount": 1, "speechCount": 1},
                    "debate_section_id": "dbsect_11",
                    "debate_type": "debate",
                    "data_uri": "https://something123919230192.com",
                    "parent_debate_section": None,
                    "show_as": "something",
                    "speakers": [],
                    "speeches": [],
                    "loaded": False,
                }
            ).serialize(),
            {
                "bill": None,
                "contains_debate": True,
                "counts": {"speakerCount": 1, "speechCount": 1},
                "data_uri": "https://something123919230192.com",
                "debate_section_id": "dbsect_11",
                "debate_type": "debate",
                "parent_debate_section": None,
                "show_as": "something",
                "speakers": [],
                "speeches": [],
            },
        )

    def test_pdf_obj(self):
        section = DebateSection(
            show_as="test",
            pdf_location=os.path.join(self.resources_pdf_path, "2021-11-18.pdf"),
        )
        self.assertEqual(
            section.pdf_obj.section_headers,
            [
                "Gnó an tSeanaid - Business of Seanad",
                "Nithe i dtosach suíonna - Commencement Matters",
                "School Enrolments",
                "National Asset Management Agency",
                "General Practitioner Services",
                "Equality Issues",
                "Gnó an tSeanaid - Business of Seanad",
                "An tOrd Gnó - Order of Business",
                "Address to Seanad Éireann by An Taoiseach",
                "Air Accident Investigation Unit Final Report into R116 Air Accident: Statements",
            ],
        )

    @skip("todo")
    def test_speech_contains(self):
        pass
