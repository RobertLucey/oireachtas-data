import os
import re
import logging
from functools import lru_cache

import ujson
import edlib
import unidecode

from oireachtas_data.constants import MEMBERS_DIR

logger = logging.getLogger(__name__)


class Members:
    def __init__(self):
        self.loaded = False
        self.data = []

    def append(self, member):
        self.data.append(member)

    def serialize(self):
        return [m.serialize() for m in self.data]

    def write(self):
        os.makedirs(MEMBERS_DIR, exist_ok=True)
        with open(os.path.join(MEMBERS_DIR, "members.json"), "w") as f:
            f.write(ujson.dumps(self.serialize()))

    def load(self):
        if self.loaded:
            return

        if os.path.exists(os.path.join(MEMBERS_DIR, "members.json")):
            with open(os.path.join(MEMBERS_DIR, "members.json"), "r") as f:
                data = ujson.loads(f.read())
                for d in data:
                    self.data.append(Member(**d))
        self.loaded = True

    @lru_cache(maxsize=10000)
    def get_member(self, member_str):
        if member_str.startswith("#"):
            return self.get_member_from_id(member_str)
        return self.get_member_from_name(member_str)

    @staticmethod
    def clean_name(name):
        # TODO: Give back some options rather than a single name

        # If a minister is specified it usually looks like:
        # Minister for Something (Deputy Joan Malone)
        if "Minister" in name:
            try:
                name = re.findall(r"\((.*?)\)", name)[0]
            except Exception:
                pass

        name = name.replace(")", "")
        name = name.replace("(", "")
        name = name.replace("Deputy ", "")
        name = name.replace("Senator ", "")
        name = name.replace("Mr. ", "")
        name = name.replace("Ms. ", "")
        name = name.replace("Mrs. ", "")
        name = name.replace(" ", "")
        name = name.replace(".", "")
        name = name.replace("Acting Chairman", "")

        # Remove fadas
        name = unidecode.unidecode(name)

        name = name.replace("'", "")

        return name.strip()

    @lru_cache(maxsize=10000)
    def get_member_from_name(self, name):
        if name and name[0].islower():
            # Fairly confident it's not a valid name. Look into better parsing
            return

        original_name = name
        name = self.clean_name(name)

        if not name:
            return

        exact = [member for member in self.data if member.pid == name]
        if exact:
            return self._unique_match(original_name, exact)

        aliases = (f"{name}FF", f"{name}LAB", f"{name}FG", f"{name}SF", f"Dr{name}")
        matches = [
            member for member in self.data
            if member.pid in aliases or (member.pid and f"Ms{member.pid}" == name)
        ]
        if matches:
            return self._unique_match(original_name, matches)

        distances = []
        for member in self.data:
            member_pid = member.pid
            if not member_pid or len(set(member_pid).symmetric_difference(name)) > 2:
                continue
            distance = edlib.align(member_pid, name)["editDistance"]
            if distance < 4:
                distances.append((distance, member))

        if distances:
            best_distance = min(distance for distance, _ in distances)
            return self._unique_match(
                original_name,
                [member for distance, member in distances if distance == best_distance],
            )

    @staticmethod
    def _unique_match(name, matches):
        if len(matches) == 1:
            return matches[0]
        logger.warning(
            "Ambiguous member name %r matches %s",
            name,
            [(member.pid, member.member_code) for member in matches],
        )
        return None

    @lru_cache(maxsize=10000)
    def get_member_from_id(self, pid):
        pid = pid.lstrip("#")

        matches = [member for member in self.data if member.pid == pid or member.member_code == pid]
        if matches:
            return self._unique_match(pid, matches)

    @lru_cache(maxsize=10000)
    def parties_of_member(self, member):
        if isinstance(member, str):
            member = self.get_member_from_name(member)
            if member is None:
                return None

        parties = []
        for membership in member.memberships:
            parties.append(membership.parties[0].party_code)

        return parties


class Member:
    __slots__ = (
        "date_of_death",
        "first_name",
        "last_name",
        "full_name",
        "gender",
        "member_code",
        "_pid",
        "memberships",
        "_set_pid",
    )

    def __init__(self, **kwargs):
        self.date_of_death = kwargs.get(
            "dateOfDeath", kwargs.get("date_of_death", None)
        )
        self.first_name = kwargs.get("firstName", kwargs.get("first_name", None))
        self.last_name = kwargs.get("lastName", kwargs.get("last_name", None))
        self.full_name = kwargs.get("fullName", kwargs.get("full_name", None))
        self.gender = kwargs.get("gender")
        self.member_code = kwargs.get("memberCode", kwargs.get("member_code", None))
        self._pid = kwargs.get("pId", kwargs.get("pid", None))
        self._set_pid = None

        self.memberships = []
        for membership in kwargs["memberships"]:
            if "membership" in membership:
                self.memberships.append(Membership(**membership["membership"]))
            else:
                self.memberships.append(Membership(**membership))

    def __repr__(self):
        return f"Member({self.full_name!r})"

    @property
    def pid(self):
        if self._set_pid:
            return self._set_pid

        if self._pid and self._pid[0] == "#":
            self._set_pid = self._pid.replace("#", "")
            return self._set_pid

        self._set_pid = self._pid
        return self._set_pid

    def serialize(self):
        return {
            "date_of_death": self.date_of_death,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "gender": self.gender,
            "member_code": self.member_code,
            "pid": self.pid,
            "memberships": [m.serialize() for m in self.memberships],
        }


class House:
    __slots__ = ("chamber_type", "house_code", "house_no", "show_as")

    def __init__(self, **kwargs):
        self.chamber_type = kwargs.get("chamberType", kwargs.get("chamber_type", None))
        self.house_code = kwargs.get("houseCode", kwargs.get("house_code", None))
        self.house_no = kwargs.get("houseNo", kwargs.get("house_no", None))
        self.show_as = kwargs.get("showAs", kwargs.get("show_as", None))

    def serialize(self):
        return {
            "chamber_type": self.chamber_type,
            "house_code": self.house_code,
            "house_no": self.house_no,
            "show_as": self.show_as,
        }


class Party:
    __slots__ = ("date_start", "date_end", "party_code", "show_as")

    def __init__(self, **kwargs):
        if "party" in kwargs:
            base = kwargs["party"]

            date_range = base["dateRange"]

            self.date_start = date_range["start"]
            self.date_end = date_range["end"]

            self.party_code = base["partyCode"]
            self.show_as = base["showAs"]

        else:
            self.date_start = kwargs["date_start"]
            self.date_end = kwargs["date_end"]

            self.party_code = kwargs["party_code"]
            self.show_as = kwargs["show_as"]

    def serialize(self):
        return {
            "date_start": self.date_start,
            "date_end": self.date_end,
            "party_code": self.party_code,
            "show_as": self.show_as,
        }


class Represents:
    __slots__ = ("represent_code", "represent_type", "show_as")

    def __init__(self, **kwargs):
        if "represent" in kwargs:
            base = kwargs["represent"]

            self.represent_code = base["representCode"]
            self.represent_type = base["representType"]
            self.show_as = base["showAs"]

        else:
            self.represent_code = kwargs["represent_code"]
            self.represent_type = kwargs["represent_type"]
            self.show_as = kwargs["show_as"]

    def serialize(self):
        return {
            "represent_code": self.represent_code,
            "represent_type": self.represent_type,
            "show_as": self.show_as,
        }


class Membership:
    __slots__ = ("date_start", "date_end", "house", "offices", "parties", "represents")

    def __init__(self, **kwargs):
        if "dateRange" in kwargs:
            date_range = kwargs["dateRange"]
            self.date_start = date_range.get("start", None)
            self.date_end = date_range.get("end", None)
        else:
            self.date_start = kwargs["date_start"]
            self.date_end = kwargs["date_end"]

        self.house = House(**kwargs["house"])

        self.offices = []
        self.parties = []
        for party in kwargs["parties"]:
            self.parties.append(Party(**party))

        self.represents = []
        for rep in kwargs["represents"]:
            self.represents.append(Represents(**rep))

    def serialize(self):
        return {
            "date_start": self.date_start,
            "date_end": self.date_end,
            "house": self.house.serialize(),
            "offices": [o.serialize() for o in self.offices],
            "parties": [p.serialize() for p in self.parties],
            "represents": [r.serialize() for r in self.represents],
        }


members = Members()
