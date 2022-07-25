from unittest import TestCase

from oireachtas_data.models.para import Para


class ParaTest(TestCase):
    def test_hash(self):
        self.assertEqual(
            Para.parse(
                dict(title="four", eid="five", content="six seven")
            ).content_hash,
            287143648808622511516264574481603430494,
        )

    def test_parse(self):
        self.assertEqual(
            Para.parse(dict(title="four", eid="five", content="six seven")).serialize(),
            dict(title="four", eid="five", content="six seven"),
        )

    def test_serialize(self):
        self.assertEqual(
            Para(title="four", eid="five", content="six seven").serialize(),
            dict(title="four", eid="five", content="six seven"),
        )

    def test_words(self):
        self.assertEqual(
            Para(title="four", eid="five", content="six seven").words,
            "six seven".split(),
        )

    def test_tokens(self):
        self.assertEqual(
            Para(title="four", eid="five", content="six seven").tokens,
            [("six", "CD"), ("seven", "CD")],
        )
