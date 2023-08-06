import os
import filecmp
import datetime
from urllib.request import Request, urlopen

import ujson

from unittest import TestCase, skip

from oireachtas_data.models.debate import Debate
from oireachtas_data.constants import OIREACHTAS_DIR, BASE_DIR, MEMBERS_DIR, DEBATES_DIR


class DebateTest(TestCase):
    def setUp(self):
        self.resources_path = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "test/resources/",
        )

        self.resources_pdf_path = os.path.join(self.resources_path, "pdfs")
        self.resources_json_path = os.path.join(self.resources_path, "json")

        import shutil

        shutil.rmtree(BASE_DIR)
        os.makedirs(BASE_DIR, exist_ok=True)
        os.makedirs(OIREACHTAS_DIR, exist_ok=True)
        os.makedirs(DEBATES_DIR, exist_ok=True)
        os.makedirs(MEMBERS_DIR, exist_ok=True)

        import requests
        from oireachtas_data.models.member import Members, Member

        chambers = ["dail", "seanad"]
        base_url = "https://api.oireachtas.ie/v1/members?date_start=1900-01-01&chamber_id=&chamber={chamber}&date_end=2099-01-01&limit=9999"
        members = Members()
        for chamber in chambers:
            url = base_url.format(chamber=chamber)
            result = requests.get(url)
            for result in result.json()["results"]:
                member = Member(**result["member"])
                members.append(member)
        members.write()

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
            "/tmp/oireachtas_data/0/debates/debate_Dáil Éireann_2016-05-25.pdf",
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

    def test_timestamp(self):
        debate = Debate.parse(
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
        )
        self.assertEqual(debate.timestamp, datetime.datetime(2020, 1, 1, 0, 0))

    def test_json_location(self):
        d1 = Debate()
        d1.set_filepath("asd")
        self.assertEqual(d1.json_location, "asd")

        d2 = Debate(chamber="one", date="two")
        self.assertEqual(
            d2.json_location, "/tmp/oireachtas_data/0/debates/debate_one_two.json"
        )

    def test_split_member_lines(self):
        """
        For when a member line wraps like:

        Deputy something something something (Firstname
        Lastname): Hello
        """

        chamber_id = ""
        date_start = "2011-01-19"
        date_end = "2011-01-19"
        limit = 10
        chamber = "dail"
        chamber_type = "house"  # / committee

        req = Request(
            "https://api.oireachtas.ie/v1/debates?chamber_type=%s&chamber_id=%s&chamber=%s&date_start=%s&date_end=%s&limit=%s"
            % (chamber_type, chamber_id, chamber, date_start, date_end, limit),
            headers={"accept": "application/json"},
        )
        response = urlopen(req)
        data = ujson.loads(response.read())

        debates = []
        for debate in data["results"]:
            debates.append(
                Debate(
                    date=debate["contextDate"],
                    chamber=debate["debateRecord"]["chamber"]["showAs"],
                    counts=debate["debateRecord"]["counts"],
                    debate_type=debate["debateRecord"]["debateType"],
                    debate_sections=debate["debateRecord"]["debateSections"],
                )
            )

        self.assertEqual(len(debates), 1)

        debate = debates[0]

        debate.load_data()
        debate.write()

        debate_sections = debate.debate_sections

        questionable_section = [
            d for d in debate_sections if d.debate_section_id == "dbsect_138"
        ][0]

        self.assertEqual(
            [speech["by"] for speech in questionable_section.serialize()["speeches"]],
            [
                "Minister of State at the Department of Enterprise, Trade and Innovation (Deputy Dara Calleary)"
            ],
        )
