from unittest import TestCase, skip

from oireachtas_data.utils import (
    merge_paras,
    get_file_content,
    get_debates,
    window,
    first_occuring
)


class UtilsTest(TestCase):

    @skip('TODO')
    def test_merge_paras(self):
        pass

    @skip('TODO')
    def test_get_file_content(self):
        pass

    @skip('TODO')
    def test_get_debates(self):
        pass

    def test_window(self):
        self.assertEqual(
            list(window(range(10), window_size=2)),
            [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8), (8, 9)]
        )

    def test_first_occuring(self):
        self.assertEqual(
            first_occuring(
                ['three', 'two'],
                'one two three four'
            ),
            (4, 'two')
        )
