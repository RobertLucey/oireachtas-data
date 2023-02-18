from unittest import TestCase

from oireachtas_data.models.speech import Speech
from oireachtas_data.models.para import Para


class SpeechTest(TestCase):
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
            },
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
