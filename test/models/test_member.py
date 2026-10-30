from unittest import TestCase

from oireachtas_data.models.member import Member, Members


class MembersTest(TestCase):
    SAMPLE_MEMBERS_CONTENT = [
        {
            "date_of_death": None,
            "first_name": "Pádraic",
            "last_name": "Ó Maille",
            "full_name": "Pádraic Ó Maille",
            "gender": "",
            "member_code": "Pádraic-Ó-Maille.D.1919-01-21",
            "pid": "PadraicOMaille",
            "memberships": [
                {
                    "date_start": "1944-08-18",
                    "date_end": "1946-01-19",
                    "house": {
                        "chamber_type": "house",
                        "house_code": "seanad",
                        "house_no": "5",
                        "show_as": "5th Seanad",
                    },
                    "offices": [],
                    "parties": [
                        {
                            "date_start": "1944-08-18",
                            "date_end": "1946-01-19",
                            "party_code": "Fianna_Fáil",
                            "show_as": "Fianna Fáil",
                        }
                    ],
                    "represents": [
                        {
                            "represent_code": "Nominated-by-the-Taoiseach",
                            "represent_type": "panel",
                            "show_as": "Nominated by the Taoiseach",
                        }
                    ],
                }
            ],
        },
        {
            "date_of_death": None,
            "first_name": "Labhrás",
            "last_name": "Ó Murchú",
            "full_name": "Labhrás Ó Murchú",
            "gender": "",
            "member_code": "Labhrás-Ó-Murchú.S.1997-09-17",
            "pid": "LabhrasOMurchu",
            "memberships": [
                {
                    "date_start": "1997-09-17",
                    "date_end": "2002-06-26",
                    "house": {
                        "chamber_type": "house",
                        "house_code": "seanad",
                        "house_no": "21",
                        "show_as": "21st Seanad",
                    },
                    "offices": [],
                    "parties": [
                        {
                            "date_start": "1997-09-17",
                            "date_end": "2002-06-26",
                            "party_code": "Fianna_Fáil",
                            "show_as": "Fianna Fáil",
                        }
                    ],
                    "represents": [
                        {
                            "represent_code": "Cultural-and-Educational-Panel",
                            "represent_type": "panel",
                            "show_as": "Cultural and Educational Panel",
                        }
                    ],
                }
            ],
        },
    ]

    MEMBERS = Members()
    MEMBERS.append(Member(**SAMPLE_MEMBERS_CONTENT[0]))
    MEMBERS.append(Member(**SAMPLE_MEMBERS_CONTENT[1]))

    def test_get_member(self):
        member = self.MEMBERS.get_member("Labhrás Ó Murchú")
        self.assertIsNotNone(member)

        member = self.MEMBERS.get_member_from_id("#LabhrasOMurchu")
        self.assertIsNotNone(member)

    def test_get_member_from_name(self):
        member = self.MEMBERS.get_member_from_name("Labhrás Ó Murchú")
        self.assertIsNotNone(member)

        # TODO: lots of other weirdness to consider here

    def test_get_member_from_id(self):
        member = self.MEMBERS.get_member_from_id("#LabhrasOMurchu")
        self.assertIsNotNone(member)

        member = self.MEMBERS.get_member_from_id("#blahblah")
        self.assertIsNone(member)

        self.assertIsNotNone(self.MEMBERS.get_member("#PadraicOMaille"))

    def test_ambiguous_name_requires_id(self):
        members = Members()
        first = Member(**{
            **self.SAMPLE_MEMBERS_CONTENT[0],
            "pid": "PadraicOMailleFF",
        })
        second = Member(**{
            **self.SAMPLE_MEMBERS_CONTENT[0],
            "pid": "PadraicOMailleFG",
            "member_code": "Another-Padraic-OMaille.D.1980-01-01",
        })
        members.append(first)
        members.append(second)

        with self.assertLogs("oireachtas_data.models.member", level="WARNING") as logs:
            self.assertIsNone(members.get_member("Pádraic Ó Maille"))
        self.assertIn("Ambiguous member name", logs.output[0])
        self.assertIs(members.get_member("#PadraicOMailleFF"), first)
        self.assertIs(members.get_member("#PadraicOMailleFG"), second)

    def test_id_resolves_ambiguous_names(self):
        members = Members()
        first = Member(**self.SAMPLE_MEMBERS_CONTENT[0])
        second = Member(**{
            **self.SAMPLE_MEMBERS_CONTENT[0],
            "pid": "PadraicOMaille2",
            "member_code": "Another-Padraic-OMaille.D.1980-01-01",
        })
        members.append(first)
        members.append(second)

        self.assertIs(members.get_member("#PadraicOMaille2"), second)
        self.assertIs(members.get_member_from_id(second.member_code), second)

    def test_ambiguous_fuzzy_name(self):
        members = Members()
        first = Member(**self.SAMPLE_MEMBERS_CONTENT[0])
        second = Member(**{
            **self.SAMPLE_MEMBERS_CONTENT[0],
            "pid": "PadraicOMailly",
            "member_code": "Another-Padraic-OMailly.D.1980-01-01",
        })
        members.append(first)
        members.append(second)

        with self.assertLogs("oireachtas_data.models.member", level="WARNING"):
            self.assertIsNone(members.get_member_from_name("PadraicOMaill"))

    def test_parties(self):
        self.assertEqual(
            self.MEMBERS.parties_of_member("LabhrasOMurchu"), ["Fianna_Fáil"]
        )

    def test_clean_name(self):
        self.assertEqual(
            Members.clean_name("Minister (Padraic OMaille)"), "PadraicOMaille"
        )

    def test_serialize(self):
        serialization = self.MEMBERS.serialize()
        self.assertEqual(
            serialization,
            [
                {
                    "date_of_death": None,
                    "first_name": "Pádraic",
                    "last_name": "Ó Maille",
                    "full_name": "Pádraic Ó Maille",
                    "gender": "",
                    "member_code": "Pádraic-Ó-Maille.D.1919-01-21",
                    "pid": "PadraicOMaille",
                    "memberships": [
                        {
                            "date_start": "1944-08-18",
                            "date_end": "1946-01-19",
                            "house": {
                                "chamber_type": "house",
                                "house_code": "seanad",
                                "house_no": "5",
                                "show_as": "5th Seanad",
                            },
                            "offices": [],
                            "parties": [
                                {
                                    "date_start": "1944-08-18",
                                    "date_end": "1946-01-19",
                                    "party_code": "Fianna_Fáil",
                                    "show_as": "Fianna Fáil",
                                }
                            ],
                            "represents": [
                                {
                                    "represent_code": "Nominated-by-the-Taoiseach",
                                    "represent_type": "panel",
                                    "show_as": "Nominated by the Taoiseach",
                                }
                            ],
                        }
                    ],
                },
                {
                    "date_of_death": None,
                    "first_name": "Labhrás",
                    "last_name": "Ó Murchú",
                    "full_name": "Labhrás Ó Murchú",
                    "gender": "",
                    "member_code": "Labhrás-Ó-Murchú.S.1997-09-17",
                    "pid": "LabhrasOMurchu",
                    "memberships": [
                        {
                            "date_start": "1997-09-17",
                            "date_end": "2002-06-26",
                            "house": {
                                "chamber_type": "house",
                                "house_code": "seanad",
                                "house_no": "21",
                                "show_as": "21st Seanad",
                            },
                            "offices": [],
                            "parties": [
                                {
                                    "date_start": "1997-09-17",
                                    "date_end": "2002-06-26",
                                    "party_code": "Fianna_Fáil",
                                    "show_as": "Fianna Fáil",
                                }
                            ],
                            "represents": [
                                {
                                    "represent_code": "Cultural-and-Educational-Panel",
                                    "represent_type": "panel",
                                    "show_as": "Cultural and Educational Panel",
                                }
                            ],
                        }
                    ],
                },
            ],
        )


class MemberTest(TestCase):
    SAMPLE_MEMBER_CONTENT = {
        "date_of_death": None,
        "first_name": "Labhrás",
        "last_name": "Ó Murchú",
        "full_name": "Labhrás Ó Murchú",
        "gender": "",
        "member_code": "Labhrás-Ó-Murchú.S.1997-09-17",
        "pid": "LabhrasOMurchu",
        "memberships": [
            {
                "date_start": "1997-09-17",
                "date_end": "2002-06-26",
                "house": {
                    "chamber_type": "house",
                    "house_code": "seanad",
                    "house_no": "21",
                    "show_as": "21st Seanad",
                },
                "offices": [],
                "parties": [
                    {
                        "date_start": "1997-09-17",
                        "date_end": "2002-06-26",
                        "party_code": "Fianna_Fáil",
                        "show_as": "Fianna Fáil",
                    }
                ],
                "represents": [
                    {
                        "represent_code": "Cultural-and-Educational-Panel",
                        "represent_type": "panel",
                        "show_as": "Cultural and Educational Panel",
                    }
                ],
            }
        ],
    }

    def test_from_api(self):
        pass
        # TODO: get a sample

    def test_from_file(self):
        self.assertEqual(
            Member(**self.SAMPLE_MEMBER_CONTENT).serialize(), self.SAMPLE_MEMBER_CONTENT
        )

    def test_repr_shows_name(self):
        self.assertEqual(
            repr(Member(**self.SAMPLE_MEMBER_CONTENT)),
            "Member('Labhrás Ó Murchú')",
        )
