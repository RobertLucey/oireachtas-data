import os
import datetime
from difflib import SequenceMatcher
from collections import defaultdict

from cached_property import cached_property
import bs4

from oireachtas_data.models.speech import Speech
from oireachtas_data.models.para import Para


class Section():

    def __init__(self, data=None, title=None, date_string=None):
        self.date_string = date_string
        self.data = data
        self.title = title

    @property
    def content(self):
        split = self.data.split('\n')
        count = 0
        while self.date_string in split:
            count += 1
            if count > 1000:
                break
            idx = split.index(self.date_string)

            if idx == 0:
                split = split[1:]
            elif idx == 1:
                split = split[2:]
            elif idx == 2:
                split = split[3:]
            elif idx == 3:
                split = split[4:]
            else:

                prev2 = split[idx - 2]

                if prev2 != '':
                    continue

                # TODO: check that idx + 2 is always correct
                split = split[0:idx-4] + split[idx + 2:]

        # TODO: need to join broken sentences
        # TODO: need to remove [NAME] casue that's a page break

        final = []

        for line in split:
            if ':' in line:
                final.append(line)
            else:
                if len(final):
                    final[-1] = final[-1] + ' ' + line
                else:
                    pass  # First line has no : so possibly the question

        return '\n'.join(final)

    def non_header_content(self):
        return ''

    @cached_property
    def speeches(self):

        # FIXME if questions it goes '{int}. {NAME} the question'
        if ':' not in self.content:
            return []

        speeches = []

        lines = self.content.split('\n')
        for line in lines:
            if ':' not in line:
                continue

            person = line[:line.index(':')]
            content = line[line.index(':') + 2:]

            speeches.append(
                Speech(
                    by=person,
                    _as=None,
                    eid=None,
                    paras=[
                        Para(
                            title=None,
                            eid=None,
                            content=content
                        )
                    ]
                )
            )

        return speeches


class Page():

    def __init__(self, data, date_string):
        self.data = data
        self.date_string = date_string

    @property
    def header(self):
        from oireachtas_data.utils import find_nth
        return self.data[
            0:find_nth(self.data, '\n\n', 3)
        ].replace('\n\n' + self.date_string + '\n\n', ' ').strip()

    @property
    def sans_header(self):
        from oireachtas_data.utils import find_nth
        return self.data[find_nth(self.data, '\n\n', 3):].strip()

    def serialize(self):
        return {
            'data': self.data,
            'date_string': self.date_string,
            'sans_header': self.sans_header,
            'header': self.header
        }


class PDF():

    def __init__(self, fp):
        self.fp = fp
        self.data = None
        self.loaded = False
        self.removed_sections = []

    def load(self):
        if self.loaded:
            return

        html_file = self.fp.replace('.pdf', 's.html')

        if not os.path.exists(html_file):
            os.system(f'pdftohtml \'{self.fp}\'')

        if not os.path.exists(html_file):
            print('Could not convert pdf to html: %s' % (html_file))
            self.loaded = True
            return

        # TODO: parse xml tree
        soup = bs4.BeautifulSoup(open(html_file), 'html.parser')

        bolds = soup.find_all('b')

        possibles = []
        for bold in bolds:
            if hasattr(bold.nextSibling, 'name'):
                if bold.nextSibling.name != 'br':
                    continue

            # Is it even valid excluding these?
            if 'Deputy' in bold.text:
                continue
            if 'Minister' in bold.text:
                continue
            if 'Senator' in bold.text:
                continue

            ## Maybe exclude the following?
            #if 'Comhairle' in bold.text:
            #    continue
            #if 'Cathaoirleach' in bold.text:
            #    continue
            #if 'Taoiseach' in bold.text:
            #    continue

            # Could clean up more but not much of a point

            possibles.append(bold)

        self.possibles = possibles

        self.loaded = True

    def matching_header(self, show_as):

        self.load()

        space = '\xa0'

        # TODO: factor in removed ones

        for header in self.possibles:
            if SequenceMatcher(None, header.text.replace(space, ' '), show_as).ratio() > 0.6:
                return header.text.replace(space, ' ')

        return None

    @property
    def section_headers(self):
        if not self.loaded:
            self.load()

        if self.data is None:
            return []

        return []

    @property
    def date(self):
        return datetime.datetime.strptime(
            os.path.splitext(self.fp.split('_')[-1])[0],
            '%Y-%m-%d'
        )

    @property
    def date_string(self):
        return self.date.strftime('%-d %B %Y.')

    @property
    def debate_sections(self):
        return self._debate_sections

    @cached_property
    def _debate_sections(self):
        if not self.loaded:
            self.load()

        sections = []

        html_file = self.fp.replace('.pdf', 's.html')
        html_lines = []
        with open(html_file, 'r') as f:
            html_lines = f.readlines()

        header_line_no_map = defaultdict(list)
        line_no_header_map = {}

        last_index = 0
        for possible in self.possibles:
            for idx, line in enumerate(html_lines[last_index:]):
                # can skip a lot of stuff before parsing
                if bs4.BeautifulSoup(line, 'html.parser').text.strip() == possible.text.strip():
                    # go until the next possible and then set last index
                    last_index += idx + 1
                    possible_text = possible.text
                    header_line_no_map[possible_text.strip().replace('\xa0', ' ')].append(last_index)
                    line_no_header_map[last_index] = possible_text.strip().replace('\xa0', ' ')
                    break

        from oireachtas_data.utils import window
        for x, y in window(line_no_header_map.items(), window_size=2):
            content = html_lines[x[0]:y[0]-1]

            lines_text = [
                bs4.BeautifulSoup(c.replace('<br/>', '\n'), 'html.parser').text.strip().replace('\xa0', ' ') for c in content
            ]

            # TODO: in content need to make <br/> be a \n or else it joins directly into the next word
            sections.append(
                Section(
                    date_string=self.date_string,
                    data='\n'.join(lines_text),
                    title=x[1]
                )
            )

        for s in sections:
            s.speeches

        return sections
