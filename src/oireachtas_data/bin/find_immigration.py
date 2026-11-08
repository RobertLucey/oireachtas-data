import tqdm
import pprint
from collections import defaultdict
import datetime
from oireachtas_data.orm import OireachtasArchive

db = OireachtasArchive()
debates = db.debates
questions = db.questions


def immigration_count():

    c = 0
    g = 0
    for idx, d in tqdm.tqdm(enumerate(debates.all()), total=debates.count()):
        # TODO: token set

        import pdb; pdb.set_trace()

        c += 1
        text = d.text.lower()

        if any([
            'immigration' in text
        ]):
            g += 1

    print(f'debates: {g} {(g/c)*100}%')




def immigrant_count_since_year():

    word_counts = defaultdict(int)

    c = 0
    g = 0
    total_word_count = 0

    for idx, d in tqdm.tqdm(enumerate(debates.all()), total=debates.count()):

        if d.timestamp >= datetime.datetime(2015, 1, 1) and d.timestamp <= datetime.datetime(2025, 12, 31):

            c += 1

            text = d.text.lower()
            split_text = text.split()

            total_word_count += len(split_text)

            if 'immigr' in text:
                g += 1

                useful_words = [w.strip('-').strip('"').strip('\'').strip(';').strip(':').strip(')').strip('(').strip('.').strip(',').strip('?').strip('"').strip('“').strip('?').strip(']').strip('[') for w in split_text if 'immigr' in w]

                for useful_word in useful_words:
                    word_counts[useful_word] += 1

        print(f'{total_word_count:,}')
        print(word_counts)
        print(sum(word_counts.values()))

    print(f'debates: {c} {g} {(g/c)*100}%   {(sum(word_counts.values())/total_word_count)*100}')


def immigrant_count_by_year():

    year_data = defaultdict(lambda: defaultdict(int))

    c = 0
    g = 0
    total_word_count = defaultdict(int)

    for idx, d in tqdm.tqdm(enumerate(debates.all()), total=debates.count()):

        if d.timestamp >= datetime.datetime(2015, 1, 1) and d.timestamp < datetime.datetime(2026, 1, 1):

            c += 1

            text = d.text.lower()
            split_text = text.split()

            total_word_count[str(d.timestamp.year)] += len(split_text)

            if 'immigr' in text:
                g += 1

                useful_words = [w.strip('-').strip('"').strip('\'').strip(';').strip(':').strip(')').strip('(').strip('.').strip(',').strip('?').strip('"').strip('“').strip('?').strip(']').strip('[') for w in split_text if 'immigr' in w]

                for useful_word in useful_words:
                    year_data[str(d.timestamp.year)][useful_word] += 1


    pprint.pprint(dict(year_data))
    pprint.pprint(total_word_count)



immigrant_count_by_year()


































# as a percentage of year by count but also by word count

def find_dup_questions_count():

    text_set = {}

    dup_count = 0

    for idx, d in tqdm.tqdm(enumerate(questions.all()), total=questions.count()):

        h = hash(d.text + d.answer_text)
        if h in text_set:
            dup_count += 1

        text_set[h] = d.uri

    print(f'dups: {dup_count}')


#find_dup_questions_count()



