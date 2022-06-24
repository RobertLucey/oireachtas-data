import json
import os
import pickle
from itertools import islice

from oireachtas_data.constants import DEBATES_DIR
from oireachtas_data.models.debate import Debate
from oireachtas_data.models.para import Para


def find_nth(haystack, needle, n):
    start = haystack.find(needle)
    while start >= 0 and n > 1:
        start = haystack.find(needle, start+len(needle))
        n -= 1
    return start


def merge_paras(paras):
    '''
    When you don't care about context it's often easier to treat many
    paragraphs as one.

    :param paras:
    :return: A Para object that just merges all the paras you give it into one.
    '''
    return Para(content='\n\n'.join([m.content for m in paras]))


def get_file_content(filepath):
    """
    Read a file regardless of the extension

    For instance if there's some pickle files and some pickle.bz files
    this will give back the same data as if they were not compressed

    :param filepath: Filepath to read from
    :return: Depending on the ext it may be a pickled obj / str
    """
    ext = os.path.splitext(filepath)[1]
    if ext == '.txt':
        return open(filepath, 'r').read()
    elif ext == '.json':
        f = open(filepath, 'r')
        data = json.loads(f.read())
        f.close()
        return data
    elif ext == '.pickle':
        return pickle.load(open(filepath, 'rb'))
    else:
        raise NotImplementedError()


def iter_debates():
    for f in os.listdir(DEBATES_DIR):
        if f.endswith('.json'):
            yield Debate.from_file(
                os.path.join(
                    DEBATES_DIR,
                    f
                )
            )


def get_debates():
    debates = []
    for f in os.listdir(DEBATES_DIR):
        if f.endswith('.json'):
            debates.append(
                Debate.from_file(
                    os.path.join(
                        DEBATES_DIR,
                        f
                    )
                )
            )
    return debates


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
    earliest_idx = float('inf')
    for s in strings:
        try:
            idx = content.index(s)
            if idx < earliest_idx:
                earliest = s
                earliest_idx = idx
        except ValueError:
            pass

    return (earliest_idx, earliest)
