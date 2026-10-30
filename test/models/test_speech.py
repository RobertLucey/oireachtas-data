from unittest import TestCase
from unittest.mock import patch

from oireachtas_data import members as package_members
from oireachtas_data.models.member import members as model_members
from oireachtas_data.models.speech import Speech
from oireachtas_data.models.para import Para


class SpeechTest(TestCase):
    def test_member_uses_shared_registry(self):
        self.assertIs(package_members, model_members)
        speaker = object()
        with patch.object(model_members, "get_member", return_value=speaker) as lookup:
            self.assertIs(Speech(by="#Example", paras=[]).member_obj, speaker)
        lookup.assert_called_once_with("#Example")
        self.assertIsNone(Speech(paras=[]).member_obj)

    def test_member_code_resolves_exactly_when_available(self):
        speaker = object()
        with patch.object(
            model_members, "get_member_from_id", return_value=speaker
        ) as lookup, patch.object(model_members, "get_member") as fuzzy_lookup:
            speech = Speech(by="#MichaelHealyRae", paras=[], member_code="Michael-Healy-Rae.D.2011-03-09")
            self.assertIs(speech.member_obj, speaker)
        lookup.assert_called_once_with("Michael-Healy-Rae.D.2011-03-09")
        fuzzy_lookup.assert_not_called()

    def test_serialization_preserves_member_id(self):
        speech = Speech(by="#Example", paras=[])
        self.assertEqual(speech.by, "Example")
        self.assertEqual(speech.serialize()["by"], "#Example")
        self.assertEqual(Speech.parse(speech.serialize()).serialize()["by"], "#Example")

    def test_parse(self):
        self.assertEqual(
            Speech.parse(
                {
                    "as": "two",
                    "by": "one",
                    "eid": "three",
                    "paras": [
                        {"content": "six seven", "eid": "five", "title": "four"},
                        {"content": "ten", "eid": "nine", "title": "eight"},
                    ],
                    "member_code": "one.D.2020-01-01",
                }
            ).serialize(),
            {
                "as": "two",
                "by": "one",
                "eid": "three",
                "paras": [
                    {"content": "six seven", "eid": "five", "title": "four"},
                    {"content": "ten", "eid": "nine", "title": "eight"},
                ],
                "member_code": "one.D.2020-01-01",
            },
        )

    def test_parse_defaults_member_code_when_absent(self):
        self.assertIsNone(
            Speech.parse(
                {"as": "two", "by": "one", "eid": "three", "paras": []}
            ).member_code
        )

    def test_serialize(self):
        self.assertEqual(
            Speech(
                by="one",
                _as="two",
                eid="three",
                paras=[
                    Para(title="four", eid="five", content="six seven"),
                    Para(title="eight", eid="nine", content="ten"),
                ],
            ).serialize(),
            {
                "as": "two",
                "by": "one",
                "eid": "three",
                "paras": [
                    {"content": "six seven", "eid": "five", "title": "four"},
                    {"content": "ten", "eid": "nine", "title": "eight"},
                ],
                "member_code": None,
            },
        )

    def test_content(self):
        self.assertEqual(
            Speech(
                by="one",
                _as="two",
                eid="three",
                paras=[
                    Para(title="four", eid="five", content="six seven"),
                    Para(title="eight", eid="nine", content="ten"),
                ],
            ).content,
            "\nsix seven\n\nten",
        )
