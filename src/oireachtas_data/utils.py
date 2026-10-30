from itertools import islice

from oireachtas_data.archive import DownloadedDebates
from oireachtas_data.models.para import Para


def find_nth(haystack, needle, n):
    start = haystack.find(needle)
    while start >= 0 and n > 1:
        start = haystack.find(needle, start + len(needle))
        n -= 1
    return start


def merge_paras(paras):
    """
    When you don't care about context it's often easier to treat many
    paragraphs as one.

    :param paras:
    :return: A Para object that just merges all the paras you give it into one.
    """
    from oireachtas_data.models.para import Paras

    if isinstance(paras, Paras):
        paras = paras.data

    return Para(content="\n\n".join([m.content for m in paras]))


def iter_debates(archive_dir=None):
    """Iterate over debates from the downloaded archive."""
    return iter(DownloadedDebates(archive_dir))


def get_debates(archive_dir=None):
    """Return debates from the downloaded archive as a list."""
    return list(iter_debates(archive_dir))


def window(sequence, window_size=2):
    """
    Returns a sliding window (of width n) over data from the iterable
    """
    seq_iterator = iter(sequence)
    result = tuple(islice(seq_iterator, window_size))
    if len(result) == window_size:
        yield result
    for elem in seq_iterator:
        result = result[1:] + (elem,)
        yield result


def first_occuring(strings, content):
    earliest = None
    earliest_idx = float("inf")
    for s in strings:
        try:
            idx = content.index(s)
            if idx < earliest_idx:
                earliest = s
                earliest_idx = idx
        except ValueError:
            pass

    return (earliest_idx, earliest)
