import argparse
import datetime
import json
import os
from multiprocessing.pool import ThreadPool

import tqdm

from urllib.request import Request
from urllib.request import urlopen

from oireachtas_data.models.debate import Debate
from oireachtas_data.constants import DEBATES_DIR
from oireachtas_data.utils import get_debates


def scrape_debates(d):
    try:
        d.load_data()
        d.write()
    except:
        print('Possibly wrong pdf parsed: %s - %s' % (d.date, d.chamber))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--processes',
        type=int,
        dest='num_processes',
        default=20
    )
    args = parser.parse_args()

    if not os.path.exists(DEBATES_DIR):
        os.makedirs(DEBATES_DIR, exist_ok=True)

    earliest_possible = datetime.datetime(1900, 1, 1)
    chamber_types = ['house', 'committee']
    try:
        earliest = min([d.timestamp for d in get_debates()])
    except:
        earliest = datetime.datetime.now()

    # There are a lot of access denieds, should look here for missing data
    # https://www.oireachtas.ie/en/debates/debate/seanad/{x}/{y}/ from https://data.oireachtas.ie/akn/ie/debateRecord/seanad/{x}/debate/mul@/dbsect_{y}.xml
    # will need to parse from the page which will be anoying

    for chamber_type in chamber_types:
        while earliest > earliest_possible:
            earliest = earliest.replace(day=1)

            chamber_id = ''
            chamber = ''
            date_start = earliest.strftime('%Y-%m-%d')
            date_end = (
                (earliest + datetime.timedelta(days=32)).replace(day=1) - datetime.timedelta(days=1)
            ).strftime('%Y-%m-%d')
            limit = 1000

            print(
                'Get debates of config: %s' % (
                    {
                        'chamber_id': chamber_id,
                        'chamber': chamber,
                        'chamber_type': chamber_type,
                        'date_start': date_start,
                        'date_end': date_end,
                        'limit': limit,
                    }
                )
            )

            req = Request(
                'https://api.oireachtas.ie/v1/debates?chamber_type=%s&chamber_id=%s&chamber=%s&date_start=%s&date_end=%s&limit=%s' % (
                    chamber_type,
                    chamber_id,
                    chamber,
                    date_start,
                    date_end,
                    limit
                ),
                headers={'accept': 'application/json'}
            )
            response = urlopen(req)
            data = json.loads(response.read())

            print('got debates: %s' % (len(data['results'])))

            debates = []
            for d in data['results']:
                debates.append(
                    Debate(
                        date=d['contextDate'],
                        chamber=d['debateRecord']['chamber']['showAs'],
                        counts=d['debateRecord']['counts'],
                        debate_type=d['debateRecord']['debateType'],
                        debate_sections=d['debateRecord']['debateSections']
                    )
                )

            pool = ThreadPool(processes=args.num_processes)
            for _ in tqdm.tqdm(
                pool.imap_unordered(scrape_debates, debates),
                total=len(debates)
            ):
                pass

            earliest = earliest - datetime.timedelta(days=1)


if __name__ == '__main__':
    main()
