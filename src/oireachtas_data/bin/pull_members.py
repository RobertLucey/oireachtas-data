import os

import requests

from oireachtas_data.models.member import Members, Member
from oireachtas_data.constants import MEMBERS_DIR


def main():

    if not os.path.exists(MEMBERS_DIR):
        os.makedirs(MEMBERS_DIR, exist_ok=True)

    chambers = [
        'dail',
        'seanad'
    ]

    base_url = "https://api.oireachtas.ie/v1/members?date_start=1900-01-01&chamber_id=&chamber={chamber}&date_end=2099-01-01&limit=9999"

    members = Members()

    for chamber in chambers:
        url = base_url.format(chamber=chamber)

        result = requests.get(url)

        for result in result.json()['results']:
            member = Member(**result['member'])
            members.append(member)

    members.write()


if __name__ == '__main__':
    main()
