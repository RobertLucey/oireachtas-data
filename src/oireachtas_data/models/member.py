import json
import os
import re
from functools import lru_cache

import unidecode

from oireachtas_data.constants import MEMBERS_DIR


class Members():

    def __init__(self):
        self.loaded = False
        self.data = []

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

    @lru_cache(maxsize=500)
    def get_member(self, member_str):
        if member_str.startswith('#'):
            return self.get_member_from_id(member_str)
        else:
            return self.get_member_from_name(member_str)

    def get_member_from_name(self, name):

        # If a minister is specified it usually looks like:
        # Minister for Something (Deputy Joan Malone)
        if 'Minister' in name:
            name = re.findall('\((.*?)\)', name)

        name = name.replace('Deputy ', '')
        name = name.replace('Senator ', '')
        name = name.lstrip('Mr. ')
        name = name.lstrip('Ms. ')
        name = name.lstrip('Mrs. ')
        name = name.replace(' ', '')
        name = name.replace('\'', '')

        # Remove fadas
        name = unidecode.unidecode(name)

        for member in self.data:
            if member.pid == name:
                return member

        print('Could not find member id for "%s"' % (name,))

    def get_member_from_id(self, pid):
        pid = pid.replace('#', '')

        for member in self.data:
            if member.pid == pid:
                return member


class Member():

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
