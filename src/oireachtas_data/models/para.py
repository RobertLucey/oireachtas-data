import hashlib
from functools import lru_cache

from cached_property import cached_property

import nltk
from nltk.tag.perceptron import PerceptronTagger

from oireachtas_data.nltk_resources import ensure_resource

_NEW_NLTK_DATA = tuple(int(part) for part in nltk.__version__.split(".")[:2]) >= (3, 9)
_TAGGER_PACKAGE = "averaged_perceptron_tagger_eng" if _NEW_NLTK_DATA else "averaged_perceptron_tagger"
_PUNKT_PACKAGE = "punkt_tab" if _NEW_NLTK_DATA else "punkt"


@lru_cache(maxsize=1)
def get_tagger():
    ensure_resource(_TAGGER_PACKAGE, "taggers/" + _TAGGER_PACKAGE + "/")
    return PerceptronTagger()


def clean_content(data):
    content = data.replace("----  (Interruptions)", "").strip()

    while "  " in content:
        content = content.replace("  ", " ")

    return content


class Paras:
    def __init__(self, data=None):
        self.data = data


class Para:
    """
    Paragraph object, has a title, id, and content.

    Inherits from Text which has all the text analysis bits
    """

    __slots__ = ("title", "eid", "_content")

    def __init__(self, title=None, eid=None, content=None):
        """

        :kwarg title: Sometimes a paragraph has a title, not often
        :kwarg eid: Incremented id of the paragraph
        :kwarg content: The str text content
        """
        self.title = title
        self.eid = eid
        self._content = content

    @property
    def content(self):
        return clean_content(self._content)

    @property
    def __dict__(self):
        return self.serialize()

    @staticmethod
    def parse(data):
        return Para(title=data["title"], eid=data["eid"], content=data["content"])

    @cached_property
    def words(self):
        """

        :return: A list of nltk tokenized words
        """
        resource = (
            "tokenizers/punkt_tab/english/"
            if _NEW_NLTK_DATA
            else "tokenizers/punkt/english.pickle"
        )
        ensure_resource(_PUNKT_PACKAGE, resource)
        return nltk.word_tokenize(self.content)

    @cached_property
    def tokens(self):
        """

        :reuturn: A list of nltk tokenized words with their tag
        """
        return get_tagger().tag(self.words)

    @property
    def content_hash(self):
        return int(hashlib.md5(bytes(self.content, "utf8")).hexdigest(), 16)

    def serialize(self):
        return {"title": self.title, "eid": self.eid, "content": self.content}

    @property
    def is_valid_para(self):
        return self.content not in ("Members rose.", "Members rose and applauded.")
