import json
import os
import re
from functools import lru_cache

import edlib
import unidecode

from oireachtas_data.constants import MEMBERS_DIR


class Members():

    def __init__(self):
        self.loaded = False
        self.data = []
        self.found_member_pids = set()

    def append(self, member):
        self.data.append(member)

    def serialize(self):
        return [
            m.serialize() for m in self.data
        ]

    def write(self):
        with open(os.path.join(MEMBERS_DIR, 'members.json'), 'w') as f:
            f.write(
                json.dumps(self.serialize())
            )

    def load(self):
        if self.loaded:
            return

        if os.path.exists(os.path.join(MEMBERS_DIR, 'members.json')):
            with open(os.path.join(MEMBERS_DIR, 'members.json'), 'r') as f:
                data = json.loads(f.read())
                for d in data:
                    self.data.append(
                        Member(**d)
                    )
        self.loaded = True

    def get_member(self, member_str):
        if member_str.startswith('#'):
            return self.get_member_from_id(member_str)
        else:
            return self.get_member_from_name(member_str)

    @staticmethod
    def clean_name(name):
        # If a minister is specified it usually looks like:
        # Minister for Something (Deputy Joan Malone)
        if 'Minister' in name:
            try:
                name = re.findall('\((.*?)\)', name)[0]
            except:
                pass

        name = name.replace(')', '')
        name = name.replace('(', '')
        name = name.replace('Deputy ', '')
        name = name.replace('Senator ', '')
        name = name.replace('Mr. ', '')
        name = name.replace('Ms. ', '')
        name = name.replace('Mrs. ', '')
        name = name.replace(' ', '')

        # Remove fadas
        name = unidecode.unidecode(name)

        name = name.replace('\'', '')

        return name

    @lru_cache(maxsize=100)
    def get_probable_members(self, starting_char):
        probable_members = [m for m in self.data if m.pid is not None and m.pid[0] == starting_char]
        probable_members_pids = set([m.pid for m in probable_members])
        return probable_members, probable_members_pids

    @lru_cache(maxsize=10000)
    def get_member_from_name(self, name):

        # Some issues with michael collins since there are two
        # FIXME: Any near duplicate names should be noted.
        # if there's a number at the end we need to be very careful

        name = self.clean_name(name)

        for member in self.data:
            if member.pid is None:
                continue
            if member.pid == name:
                self.found_member_pids.add(member.pid)
                return member

        probable_members, probable_members_pids = self.get_probable_members(name[0])

        for member in probable_members:
            if member.pid is None:
                continue
            if member.pid in self.found_member_pids:
                continue
            if len(set(member.pid).symmetric_difference(name)) > 2:
                continue
            if edlib.align(member.pid, name)['editDistance'] < 4:
                self.found_member_pids.add(member.pid)
                return member

        for member in self.data:
            if member.pid is None:
                continue
            if member.pid in probable_members_pids:
                continue
            if member.pid in self.found_member_pids:
                continue
            if len(set(member.pid).symmetric_difference(name)) > 2:
                continue
            if edlib.align(member.pid, name)['editDistance'] < 4:
                self.found_member_pids.add(member.pid)
                return member

    @lru_cache(maxsize=10000)
    def get_member_from_id(self, pid):
        pid = pid.replace('#', '')

        for member in self.data:
            if member.pid == pid:
                return member

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

class Member():

    __slots__ = (
        'date_of_death',
        'first_name',
        'last_name',
        'full_name',
        'gender',
        'member_code',
        'pid',
        'memberships'
    )

    def __init__(self, *args, **kwargs):
        self.date_of_death = kwargs.get('dateOfDeath', kwargs.get('date_of_death', None))
        self.first_name = kwargs.get('firstName', kwargs.get('first_name', None))
        self.last_name = kwargs.get('lastName', kwargs.get('last_name', None))
        self.full_name = kwargs.get('fullName', kwargs.get('full_name', None))
        self.gender = kwargs.get('gender', kwargs.get('gender', None))
        self.member_code = kwargs.get('memberCode', kwargs.get('member_code', None))
        self.pid = kwargs.get('pId', kwargs.get('pid', None))

        self.memberships = []
        for membership in kwargs['memberships']:
            if 'membership' in membership:
                self.memberships.append(
                    Membership(**membership['membership'])
                )
            else:
                self.memberships.append(
                    Membership(**membership)
                )

    def serialize(self):
        return {
            'date_of_death': self.date_of_death,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.full_name,
            'gender': self.gender,
            'member_code': self.member_code,
            'pid': self.pid,
            'memberships': [
                m.serialize() for m in self.memberships
            ]

        }


class House():

    __slots__ = (
        'chamber_type',
        'house_code',
        'house_no',
        'show_as'
    )

    def __init__(self, *args, **kwargs):
        self.chamber_type = kwargs.get('chamberType', kwargs.get('chamber_type', None))
        self.house_code = kwargs.get('houseCode', kwargs.get('house_code', None))
        self.house_no = kwargs.get('houseNo', kwargs.get('house_no', None))
        self.show_as = kwargs.get('showAs', kwargs.get('show_as', None))

    def serialize(self):
        return {
            'chamber_type': self.chamber_type,
            'house_code': self.house_code,
            'house_no': self.house_no,
            'show_as': self.show_as
        }


class Party():

    __slots__ = (
        'date_start',
        'date_end',
        'party_code',
        'show_as'
    )

    def __init__(self, *args, **kwargs):

        if 'party' in kwargs:
            base = kwargs['party']

            date_range = base['dateRange']

            self.date_start = date_range['start']
            self.date_end = date_range['end']

            self.party_code = base['partyCode']
            self.show_as = base['showAs']

        else:

            self.date_start = kwargs['date_start']
            self.date_end = kwargs['date_end']

            self.party_code = kwargs['party_code']
            self.show_as = kwargs['show_as']

    def serialize(self):
        return {
            'date_start': self.date_start,
            'date_end': self.date_end,
            'party_code': self.party_code,
            'show_as': self.show_as
        }


class Represents():

    __slots__ = (
        'represent_code',
        'represent_type',
        'show_as'
    )

    def __init__(self, *args, **kwargs):
        if 'represent' in kwargs:
            base = kwargs['represent']

            self.represent_code = base['representCode']
            self.represent_type = base['representType']
            self.show_as = base['showAs']

        else:

            self.represent_code = kwargs['represent_code']
            self.represent_type = kwargs['represent_type']
            self.show_as = kwargs['show_as']

    def serialize(self):
        return {
            'represent_code': self.represent_code,
            'represent_type': self.represent_type,
            'show_as': self.show_as
        }


class Membership():

    __slots__ = (
        'date_start',
        'date_end',
        'house',
        'offices',
        'parties',
        'represents'
    )

    def __init__(self, *args, **kwargs):

        if 'dateRange' in kwargs:
            date_range = kwargs['dateRange']
            self.date_start = date_range.get('start', None)
            self.date_end = date_range.get('end', None)
        else:
            self.date_start = kwargs['date_start']
            self.date_end = kwargs['date_end']

        self.house = House(**kwargs['house'])

        self.offices = []
        for office in kwargs['offices']:
            pass  # TODO

        self.parties = []
        for party in kwargs['parties']:
            self.parties.append(
                Party(
                    **party
                )
            )

        self.represents = []
        for rep in kwargs['represents']:
            self.represents.append(
                Represents(
                    **rep
                )
            )

    def serialize(self):
        return {
            'date_start': self.date_start,
            'date_end': self.date_end,
            'house': self.house.serialize(),
            'offices': [o.serialize() for o in self.offices],
            'parties': [p.serialize() for p in self.parties],
            'represents': [r.serialize() for r in self.represents]
        }
