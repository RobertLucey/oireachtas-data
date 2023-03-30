from oireachtas_data.models.para import Para

from oireachtas_data import members


class Speech:
    __slots__ = ("_by", "_as", "eid", "paras")

    def __init__(self, by=None, _as=None, eid=None, paras=None):
        """

        :kwarg by: The name / identifier of the speaker
        :kwarg _as: The title / position of the speaker
        :kwarf eid: incrementing id of the speech
        :kwarg paras: list of Para objects
        """
        self._by = by
        self._as = _as
        self.eid = eid

        self.paras = [para for para in paras if para.is_valid_para] if paras else []

    @property
    def by(self):
        if isinstance(self._by, str) and self._by.startswith("#"):
            return self._by.replace("#", "")

        return self._by

    @staticmethod
    def parse(data):
        paras = [Para.parse(p) for p in data["paras"]]
        paras = [para for para in paras if para.is_valid_para]
        return Speech(
            by=data["by"],
            _as=data["as"],
            eid=data["eid"],
            paras=paras,
        )

    def serialize(self):
        return {
            "by": self.by,
            "as": self._as,
            "eid": self.eid,
            "paras": [p.serialize() for p in self.paras],
        }

    @property
    def content(self):
        return "\n".join(["\n" + para.content for para in self.paras])

    @property
    def member_obj(self):
        return members.get_member(self.by)
