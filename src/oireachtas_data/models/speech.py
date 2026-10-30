from oireachtas_data.models.para import Para
from oireachtas_data.models.member import members


class Speech:
    __slots__ = ("_by", "_as", "eid", "paras", "member_code")

    def __init__(self, by=None, _as=None, eid=None, paras=None, member_code=None):
        """

        :kwarg by: The name / identifier of the speaker
        :kwarg _as: The title / position of the speaker
        :kwarf eid: incrementing id of the speech
        :kwarg paras: list of Para objects
        :kwarg member_code: Exact member code resolved from the debate XML's
            TLCPerson reference table, when the document provides one.
        """
        self._by = by
        self._as = _as
        self.eid = eid
        self.member_code = member_code

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
            member_code=data.get("member_code"),
        )

    def serialize(self):
        return {
            "by": self._by,
            "as": self._as,
            "eid": self.eid,
            "paras": [p.serialize() for p in self.paras],
            "member_code": self.member_code,
        }

    @property
    def content(self):
        return "\n".join(["\n" + para.content for para in self.paras])

    @property
    def member_obj(self):
        # Loads the full historical member roster on first use rather than
        # at import time, since most callers (anything using member_code
        # via the ORM, or not touching speeches at all) never need it.
        members.load()
        if self.member_code:
            return members.get_member_from_id(self.member_code)
        return members.get_member(self._by) if self._by else None
