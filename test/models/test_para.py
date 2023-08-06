from unittest import TestCase

from oireachtas_data.models.para import Para, Paras


class ParasTest(TestCase):
    def test_paras_init(self):
        paras = Paras(
            data=[Para.parse(dict(title="four", eid="five", content="six seven"))]
        )
        # TODO: Build out paras


class ParaTest(TestCase):
    def test_contenthash(self):
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

    def test_remove_interruptions(self):
        self.assertEqual(
            Para(
                title="four", eid="five", content="blah blah----  (Interruptions)."
            ).content,
            "blah blah.",
        )

    def test_is_valid_para(self):
        self.assertTrue(
            Para(
                title="four", eid="five", content="blah blah----  (Interruptions)."
            ).is_valid_para
        )

        self.assertFalse(
            Para(title="four", eid="five", content="Members rose.").is_valid_para
        )
