import string
from collections import Counter

from cached_property import cached_property

import nltk
from nltk.tag.perceptron import PerceptronTagger

TAGGER = PerceptronTagger()


class Paras():

    def __init__(self, data=None):
        self.data = data

class Para():
    '''
    Paragraph object, has a title, id, and content.

    Inherits from Text which has all the text analysis bits
    '''

    __slots__ = (
        'title',
        'eid',
        'content'
    )

    def __init__(self, *args, **kwargs):
        '''

        :kwarg title: Sometimes a paragraph has a title, not often
        :kwarg eid: Incremented id of the paragraph
        :kwarg content: The str text content
        '''
        self.title = kwargs.get('title', None)
        self.eid = kwargs.get('eid', None)
        self.content = kwargs.get('content', None)

    @property
    def __dict__(self):
        return self.serialize()

    @staticmethod
    def parse(data):
        return Para(
            title=data['title'],
            eid=data['eid'],
            content=data['content']
        )

    @cached_property
    def words(self):
        '''

        :return: A list of nltk tokenized words
        '''
        return nltk.word_tokenize(self.content)

    @cached_property
    def tokens(self):
        '''

        :reuturn: A list of nltk tokenized words with their tag
        '''
        return TAGGER.tag(self.words)

    def serialize(self):
        return {
            'title': self.title,
            'eid': self.eid,
            'content': self.content
        }
