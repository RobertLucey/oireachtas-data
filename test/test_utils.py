from unittest import TestCase, skip

from oireachtas_data.models.para import Para, Paras
from oireachtas_data.utils import (
    merge_paras,
    get_file_content,
    get_debates,
    window,
    first_occuring,
    find_nth,
)


class UtilsTest(TestCase):
    def test_find_nth(self):
        self.assertEqual(find_nth("12321", "2", 0), 1)
        self.assertEqual(find_nth("12321", "2", 2), 3)

    def test_merge_paras_list(self):
        paras = [
            Para.parse(dict(title="four", eid="five", content="six seven")),
            Para.parse(dict(title="five", eid="six", content="eight nine")),
        ]

        merged = merge_paras(paras)

        self.assertIsInstance(merged, Para)
        self.assertEqual(merged.words, ["six", "seven", "eight", "nine"])

    def test_merge_paras_paras(self):
        paras = Paras(
            data=[
                Para.parse(dict(title="four", eid="five", content="six seven")),
                Para.parse(dict(title="five", eid="six", content="eight nine")),
            ]
        )

        merged = merge_paras(paras)

        self.assertIsInstance(merged, Para)
        self.assertEqual(merged.words, ["six", "seven", "eight", "nine"])

    @skip("TODO")
    def test_get_file_content(self):
        pass

    @skip("TODO")
    def test_get_debates(self):
        pass

    def test_window(self):
        self.assertEqual(
            list(window(range(10), window_size=2)),
            [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8), (8, 9)],
        )

    def test_first_occuring(self):
        self.assertEqual(
            first_occuring(["three", "two"], "one two three four"), (4, "two")
        )
