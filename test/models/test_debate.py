import os
import filecmp

from unittest import TestCase, skip

from oireachtas_data.models.debate import Debate
from oireachtas_data.constants import OIREACHTAS_DIR


class DebateTest(TestCase):
    def setUp(self):
        self.resources_path = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "test/resources/",
        )

        self.resources_pdf_path = os.path.join(self.resources_path, "pdf")
        self.resources_json_path = os.path.join(self.resources_path, "json")

    def test_parse(self):
        os.makedirs(OIREACHTAS_DIR, exist_ok=True)
        self.assertEqual(
            Debate.parse(
                {
                    "date": "2020-01-01",
                    "chamber": "Dáil Éireann",
                    "counts": {
                        "questionCount": 21,
                        "billCount": 15,
                        "contributorCount": 146,
                        "divisionCount": 12,
                    },
                    "sections": [],
                    "debate_type": "debate",
                    "data_uri": "https://blahblah1983he9183r9.com",
                }
            ).serialize(),
            {
                "chamber": "Dáil Éireann",
                "counts": {
                    "billCount": 15,
                    "contributorCount": 146,
                    "divisionCount": 12,
                    "questionCount": 21,
                },
                "data_uri": "https://blahblah1983he9183r9.com",
                "date": "2020-01-01",
                "debate_type": "debate",
                "sections": [],
            },
        )

    @skip("Failing on CI but passing locally")
    def test_serialize(self):
        self.assertEqual(
            Debate(
                date="2020-01-01",
                chamber="Dáil Éireann",
                counts={
                    "questionCount": 21,
                    "billCount": 15,
                    "contributorCount": 146,
                    "divisionCount": 12,
                },
                debate_sections=[],
                debate_type="debate",
                data_uri="https://blahblah1983he9183r9.com",
            ).serialize(),
            {
                "chamber": "Dáil Éireann",
                "counts": {
                    "billCount": 15,
                    "contributorCount": 146,
                    "divisionCount": 12,
                    "questionCount": 21,
                },
                "data_uri": "https://blahblah1983he9183r9.com",
                "date": "2020-01-01",
                "debate_type": "debate",
                "sections": [],
            },
        )

    def test_set_filepath(self):
        debate = Debate(
            date="2020-01-01",
            chamber="Dáil Éireann",
            counts={
                "questionCount": 21,
                "billCount": 15,
                "contributorCount": 146,
                "divisionCount": 12,
            },
            debate_sections=[],
            debate_type="debate",
            data_uri="https://blahblah1983he9183r9.com",
        )
        self.assertEqual(debate._json_location, None)
        debate.set_filepath("/path/to/something")
        self.assertEqual(debate._json_location, "/path/to/something")

    def test_from_file(self):
        debate = Debate.from_file(
            os.path.join(
                self.resources_json_path, "debate_Dáil Éireann_2016-05-25.json"
            )
        )
        self.assertEqual(debate.serialize()["chamber"], "Dáil Éireann")
        # TODO: make sure more is asserted, this just makes sure something is loaded in

    def test_write(self):
        debate = Debate.from_file(
            os.path.join(
                self.resources_json_path, "debate_Dáil Éireann_2016-05-25.json"
            )
        )
        debate.write(location="/tmp/debate.json")

        self.assertTrue(
            filecmp.cmp(
                os.path.join(
                    self.resources_json_path, "debate_Dáil Éireann_2016-05-25.json"
                ),
                debate._json_location,
            )
        )

    def test_pdf_location(self):
        debate = Debate.from_file(
            os.path.join(
                self.resources_json_path, "debate_Dáil Éireann_2016-05-25.json"
            )
        )
        self.assertEqual(
            debate.pdf_location,
            "/opt/oireachtas_data/0/debates/debate_Dáil Éireann_2016-05-25.pdf",
        )

    def test_content_by_speaker(self):
        debate = Debate.from_file(
            os.path.join(
                self.resources_json_path, "debate_Dáil Éireann_2016-05-25.json"
            )
        )
        self.assertEqual(
            list(debate.content_by_speaker.keys()),
            [
                "SeanOFearghaillFF",
                "MichaelMartin",
                "EndaKenny",
                "GerryAdams",
                "WillieODea",
                "BrendanHowlin",
                "RoisinShortall",
                "RichardBoydBarrett",
                "ThomasByrne",
                "DannyHealyRae",
                "LouiseOReilly",
                "DavidCullinane",
                "MattieMcGrath",
                "MaryLouMcDonald",
                "JoanCollins",
                "SeanCroweSF",
                "SeanSherlock",
                "RuthCoppinger",
                "BridSmith",
                "CaoimhglinOCaolain",
                "JimOCallaghan",
                "SeamusHealy",
                "LeoVaradkar",
                "JohnBrady",
                "WilliamPenrose",
                "FinianMcGrath",
                "FrankORourke",
                "MickWallace",
                "NiamhSmyth",
                "DavidStanton",
                "AlanFarrell",
                "FrancesFitzgerald",
                "JonathanOBrien",
                "MickBarry",
                "JohnLahart",
                "ClareDaly",
                "RobertTroy",
                "GinoKenny",
                "MichaelFitzmaurice",
                "EoinOBroin",
                "ThomasPringle",
                "StephenDonnelly",
                "PearseDoherty",
                "PatBuckley",
                "DonnchadhOLaoghaire",
                "DessieEllis",
                "ImeldaMunster",
                "PaschalDonohoe",
                "TonyMcLoughlin",
                "BernardJDurkan",
                "MichaelWDArcy",
                "DamienEnglishFG",
                "SimonCoveney",
                "TimDooley",
            ],
        )

        # TODO: assert the content in these speakers
