import re
import os
import datetime

import pdftotext
from cached_property import cached_property

from oireachtas_data.utils import window
from oireachtas_data.models.speech import Speech
from oireachtas_data.models.para import Para
from oireachtas_data.models.debate_section import DebateSection


class Section():

    def __init__(self, data=None, title=None, next_title=None):
        self.data = data
        self.title = title
        self.next_title = next_title

    @property
    def content(self):

        lines = self.non_header_content.split('\n')

        valid_lines = []
        for line in lines:
            good = True

            try:
                int(line[0])
                datetime.datetime.strptime(
                    line.strip()[:10],
                    '%d/%m/%Y'
                )
                good = False
            except ValueError:
                pass

            if good:
                valid_lines.append(line)

        content = '\n'.join(valid_lines)

        if self.next_title is None:
            data = content[
                content.index(self.title) + len(self.title) + 1:
            ]

        else:
            if self.title not in content or self.next_title not in content:

                lines = content.split('\n')

                start_index = None
                end_index = None

                if self.title not in content:
                    for p, n in window(lines, window_size=2):
                        if p + ' ' + n == self.title:
                            start_index = content.index(p + '\n' + n)
                else:
                    start_index = content.index(self.title)

                if self.next_title not in content:
                    for p, n in window(lines, window_size=2):
                        if p + ' ' + n == self.next_title:
                            end_index = content.index(p + '\n' + n)
                else:
                    end_index = content.index(self.next_title)

                data = content[
                    start_index + len(self.title) + 1:end_index
                ]
            else:
                data = content[
                    content.index(self.title) + len(self.title) + 1:content.index(self.next_title)
                ]

        # Remove tables of names from voting
        while 'The Dáil divided: Tá,' in data:
            table_start = data.index('The Dáil divided: Tá,')
            if 'Question declared carried.' in data:
                table_end = data.index('Question declared carried.')
            elif 'Amendment declared lost.' in data:
                table_end = data.index('Amendment declared lost.')
            else:
                break

            start = data[:table_start]
            end = data[table_end + 5:]

            data = start + '\n\n' + end

        return data

    @cached_property
    def non_header_content(self):
        start_headers = [
            'Insert Date Here\n',
            '(OFFICIAL REPORT—Unrevised)'
        ]

        header_start = None
        for i in start_headers:
            try:
                header_start = self.data[
                    self.data.index(i) + len(i) + 1:
                ]
            except ValueError:
                pass

        header_end = '\n\n'
        data = header_start[header_start.index(header_end):]

        return data

    @property
    def speeches(self):
        if ':' not in self.data:
            return []

        first_line = self.data[
            :self.data.index(':')
        ]

        if '\n' not in first_line:
            # Can we just use 0 idx?
            return []

        first_newline = first_line.rindex('\n')

        data = self.data[
            first_newline:
        ]

        lines = data.split('\n')
        new_lines = []
        for line in lines:
            if ':' in line and any([
                'Deputy' in line,
                line[:line.index(':')].strip().split(' ')[-1][0].isupper()
            ]):
                new_lines.append(line)
            else:
                if len(new_lines):
                    new_lines[-1] = new_lines[-1] + ' ' + line

        speeches = []
        for line in new_lines:
            person = line[0:line.index(':')].strip()
            content = line[line.index(':') + 1:].strip()
            speeches.append(
                Speech(
                    by=person,
                    _as=None,
                    eid=None,
                    paras=[Para(title=None, eid=None, content=content)]
                )
            )

        return speeches


class PDF():

    def __init__(self, fp):
        self.fp = fp
        self.debate_sections = []
        self.load()

    def load(self):
        text_file = self.fp + '.txt'

        if not os.path.exists(text_file):

            with open(self.fp, 'rb') as f:
                pdf = pdftotext.PDF(f)
                content = '\n'.join([p for p in pdf])

                tf = open(text_file, 'w')
                tf.write(content)
                tf.close()

        f = open(text_file, 'r')
        self.data = f.read()
        f.close()

        self.data = self.data.replace('----', '')
        self.data = self.data.replace('\x0c', '')

        self.data = re.sub('\\d+\\/\\d+\\/\\d+[A-Za-z]+\\d+', '', self.data)

        lines = self.data.split('\n')
        good_lines = []
        for line in lines:
            good = True
            try:
                int(line[0])
                datetime.datetime.strptime(
                    line.strip(),
                    '%d %B %Y'
                )
                good = False
            except:
                pass

            if line.strip() == 'Dáil Éireann':
                good = False

            if good:
                good_lines.append(line)

        lines = good_lines
        good_lines = []

        for line in lines:
            try:
                int(line)
                good_lines.append('[PAGEBREAK]')
            except ValueError:
                good_lines.append(line)

        self.data = '\n'.join(good_lines)

    @property
    def section_headers(self):
        start_headers = [
            'Insert Date Here\n',
            '(OFFICIAL REPORT—Unrevised)'
        ]

        header_start = None
        for i in start_headers:
            try:
                header_start = self.data[
                    self.data.index(i) + len(i) + 1:
                ]
            except ValueError:
                pass

        header_end = '\n\n'
        header = header_start[:header_start.index(header_end)]

        header = header.replace('�', '')

        headers = []

        dirty_headers = header.split('\x08')
        for header in dirty_headers:
            if '\x08' in header:
                header = header[:header.index('\x08')].replace('\n', ' ')
            header = ' '.join(header.strip().split('\n')[1:]).strip()

            if header:
                try:
                    int(header[0])
                    datetime.datetime.strptime(header, '%d/%m/%YA%M%S0')
                except ValueError:
                    headers.append(header)

        return headers

    @property
    def timestamp(self):
        return datetime.datetime.strptime(
            self.data[:self.data.index('\n\n')].replace('\n', ' ').replace(',', ''),
            '%A %d %B %Y'
        )

    @property
    def debate_sections(self):
        sections = []
        for title, next_title in window(self.section_headers + [None], window_size=2):
            sections.append(
                Section(
                    data=self.data,
                    title=title,
                    next_title=next_title
                )
            )
        return sections
