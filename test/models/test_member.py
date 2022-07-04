from unittest import TestCase, skip

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
              "show_as": "5th Seanad"
            },
            "offices": [],
            "parties": [
              {
                "date_start": "1944-08-18",
                "date_end": "1946-01-19",
                "party_code": "Fianna_Fáil",
                "show_as": "Fianna Fáil"
              }
            ],
            "represents": [
              {
                "represent_code": "Nominated-by-the-Taoiseach",
                "represent_type": "panel",
                "show_as": "Nominated by the Taoiseach"
              }
            ]
          }
        ]
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
              "show_as": "21st Seanad"
            },
            "offices": [],
            "parties": [
              {
                "date_start": "1997-09-17",
                "date_end": "2002-06-26",
                "party_code": "Fianna_Fáil",
                "show_as": "Fianna Fáil"
              }
            ],
            "represents": [
              {
                "represent_code": "Cultural-and-Educational-Panel",
                "represent_type": "panel",
                "show_as": "Cultural and Educational Panel"
              }
            ]
          }
        ]
      }
    ]

    MEMBERS = Members()
    MEMBERS.append(Member(**SAMPLE_MEMBERS_CONTENT[0]))
    MEMBERS.append(Member(**SAMPLE_MEMBERS_CONTENT[1]))

    def test_get_member(self):
        member = self.MEMBERS.get_member('Labhrás Ó Murchú')
        self.assertIsNotNone(member)

        member = self.MEMBERS.get_member_from_id('#LabhrasOMurchu')
        self.assertIsNotNone(member)

    def test_get_member_from_name(self):
        member = self.MEMBERS.get_member_from_name('Labhrás Ó Murchú')
        self.assertIsNotNone(member)

    def test_get_member_from_id(self):
        member = self.MEMBERS.get_member_from_id('#LabhrasOMurchu')
        self.assertIsNotNone(member)

        member = self.MEMBERS.get_member_from_id('#blahblah')
        self.assertIsNone(member)

    def test_parties(self):
        self.assertEqual(
            self.MEMBERS.parties_of_member('LabhrasOMurchu'),
            ['Fianna_Fáil']
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
            "show_as": "21st Seanad"
          },
          "offices": [],
          "parties": [
            {
              "date_start": "1997-09-17",
              "date_end": "2002-06-26",
              "party_code": "Fianna_Fáil",
              "show_as": "Fianna Fáil"
            }
          ],
          "represents": [
            {
              "represent_code": "Cultural-and-Educational-Panel",
              "represent_type": "panel",
              "show_as": "Cultural and Educational Panel"
            }
          ]
        }
      ]
    }

    def test_from_api(self):
        pass
        # TODO: get a sample

    def test_from_file(self):
        self.assertEqual(
            Member(**self.SAMPLE_MEMBER_CONTENT).serialize(),
            self.SAMPLE_MEMBER_CONTENT
        )
