import os
import pickle
from itertools import islice
from collections import defaultdict

import edlib
import ujson

from oireachtas_data import logger
from oireachtas_data.constants import DEBATES_DIR
from oireachtas_data.models.debate import Debate
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


def get_file_content(filepath):
    """
    Read a file regardless of the extension

    For instance if there's some pickle files and some pickle.bz files
    this will give back the same data as if they were not compressed

    :param filepath: Filepath to read from
    :return: Depending on the ext it may be a pickled obj / str
    """
    ext = os.path.splitext(filepath)[1]
    if ext == ".txt":
        return open(filepath, "r").read()
    elif ext == ".json":
        f = open(filepath, "r")
        data = ujson.loads(f.read())
        f.close()
        return data
    elif ext == ".pickle":
        return pickle.load(open(filepath, "rb"))
    else:
        raise NotImplementedError()


def iter_debates():
    for f in os.listdir(DEBATES_DIR):
        if f.endswith(".json"):
            yield Debate.from_file(os.path.join(DEBATES_DIR, f))


def get_debates():
    debates = []
    for f in os.listdir(DEBATES_DIR):
        if f.endswith(".json"):
            debates.append(Debate.from_file(os.path.join(DEBATES_DIR, f)))
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


def get_duplicate_sections_of_debate(debate):
    skip = []

    data = defaultdict(list)

    sections_content = {}

    for section in debate.debate_sections:
        if section.content and len(section.content) > 100:
            key = f"{section.show_as}___{section.debate_section_id}"
            sections_content[key] = section.content

    for section in debate.debate_sections:
        key = f"{section.show_as}___{section.debate_section_id}"
        if section.content and len(section.content) > 100:
            for cmp_key, cmp_section_content in sections_content.items():
                if key == cmp_key:
                    continue

                if f"{key}___{cmp_key}" in skip:
                    continue

                section_content = section.content

                if abs(len(section_content) - len(cmp_section_content)) > 500:
                    # Big diff in size, carry on
                    continue

                # Do on the first 1k chars as a way of exiting early
                if (
                    len(section_content) > 3000
                    and len(cmp_section_content) > 3000
                    and edlib.align(section_content[:1000], cmp_section_content[:1000])[
                        "editDistance"
                    ]
                    > 100
                ):
                    continue

                elif (
                    edlib.align(section_content, cmp_section_content)["editDistance"]
                    < 100
                ):
                    data["matches"].append((key, cmp_key))
                    skip.append(f"{key}___{cmp_key}")
                    skip.append(f"{cmp_key}___{key}")
                    logger.warning(f"{debate.json_location}: {key} ~= {cmp_key}")

    return data
