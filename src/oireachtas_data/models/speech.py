from oireachtas_data.models.para import Para

from oireachtas_data import members


class Speech():

    __slots__ = (
        'by',
        '_as',
        'eid',
        'paras'
    )

    def __init__(self, by=None, _as=None, eid=None, paras=None):
        '''

        :kwarg by: The name / identifier of the speaker
        :kwarg _as: The title / position of the speaker
        :kwarf eid: incrementing id of the speech
        :kwarg paras: list of Para objects
        '''
        self.by = by
        self._as = _as
        self.eid = eid

        if paras is not None and paras != []:
            types = list(set([type(p) for p in paras]))
            assert(len(types) == 1)
            assert(types[0] == Para)

        self.paras = paras if paras else []

    @staticmethod
    def parse(data):
        return Speech(
            by=data['by'],
            _as=data['as'],
            eid=data['eid'],
            paras=[Para.parse(p) for p in data['paras']]
        )

    def serialize(self):
        return {
            'by': self.by,
            'as': self._as,
            'eid': self.eid,
            'paras': [p.serialize() for p in self.paras]
        }

    @property
    def content(self):
        return '\n'.join([
            '\n' + para.content for para in self.paras
        ])

    @property
    def member_obj(self):
        return members.get_member(self.by)
