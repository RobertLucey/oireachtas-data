from unittest import TestCase, skip

from oireachtas_data.models.debate_section import DebateSection


class DebateSectionTest(TestCase):
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

    @skip("todo")
    def test_speech_contains(self):
        pass

    @skip("todo")
    def test_load_data(self):
        pass
