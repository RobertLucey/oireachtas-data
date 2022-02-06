import re
import os
import datetime

from cached_property import cached_property

from oireachtas_data.models.speech import Speech
from oireachtas_data.models.para import Para


class Section():

    def __init__(self, data=None, title=None, next_title=None):
        self.data = data
        self.title = title
        self.next_title = next_title

    @property
    def content(self):
        from oireachtas_data.utils import first_occuring

        lines = self.non_header_content.split('\n')

        valid_lines = []
        for line in lines:
            line = line.strip()
            good = True

            try:
                int(line[0])
                datetime.datetime.strptime(
                    line.strip()[:10],
                    '%d/%m/%Y'
                )
                good = False
            except (ValueError, IndexError):
                pass

            if good:
                valid_lines.append(line)

        content = '\n'.join(valid_lines)

        data = ''

        if self.next_title is None:
            try:
                data = content[
                    content.index(self.title) + len(self.title) + 1:
                ]
            except:
                print('oops, could not find the last section')
        else:
            if self.title not in content or self.next_title not in content:

                lines = content.split('\n')

                start_index = None
                end_index = None

                if self.title not in content:
                    from oireachtas_data.utils import window
                    for p, n in window(lines, window_size=2):
                        if p + ' ' + n == self.title:
                            start_index = content.index(p + '\n' + n)
                else:
                    start_index = content.index(self.title)

                if start_index is None:
                    print(f'Could not get {self.title} from content')
                    return ''

                if self.next_title not in content:
                    from oireachtas_data.utils import window
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
        while 'The Dáil divided: Tá,' in data or 'The Committee divided: Tá,' in data or 'The Seanad divided: Tá,' in data:
            earliest = first_occuring(['The Dáil divided: Tá,', 'The Committee divided: Tá,', 'The Seanad divided: Tá,'], data)
            first_occuring_string = earliest[1]

            table_start = data.index(first_occuring_string)

            earliest = first_occuring(['Question declared carried.', 'Amendment declared lost.'], data[table_start:])
            if earliest[1] is None:
                break

            table_end = earliest[0]

            start = data[:table_start]
            end = data[table_start + table_end + 5:]

            data = start + '\n\n' + end

        data = ' '.join(data.split('[PAGEBREAK]'))

        return data.strip()

    def __del__(self):
        attrs_to_del = [
            'non_header_content'
        ]

        for attr in attrs_to_del:
            try:
                delattr(self, attr)
            except AttributeError:
                pass

    @cached_property
    def non_header_content(self):
        return self.data[
            self.data.rindex('����������������������������������'):
        ]

    @property
    def speeches(self):
        if ':' not in self.content:
            return []

        first_line = self.content[
            :self.content.index(':')
        ]

        # FIXME: this is a bit risky if the first line begins with 'name: speech'
        if '\n' not in first_line:
            # Can we just use 0 idx?
            return []

        first_newline = first_line.rindex('\n')

        data = self.content[
            first_newline:
        ]

        lines = data.split('\n')
        new_lines = []
        for line in lines:
            line = line.strip()
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
        self.data = None
        self.loaded = False

    def load(self):
        text_file = self.fp + '.txt'

        if not os.path.exists(text_file):
            with open(self.fp, 'rb') as f:
                os.system(f'pdftotext \'{self.fp}\' \'{text_file}\'')

        f = open(text_file, 'r')
        self.data = f.read()
        f.close()

        # Just weird thigs to remove, probably wobblyness in conversion to text
        self.data = self.data.replace('-----', ' — ')  # interruption / continuation of interruption
        self.data = self.data.replace('\x0c', '')

        # Removes timestamps of speach
        self.data = re.sub('\\d+\\/\\d+\\/\\d+[A-Za-z]+\\d+', '', self.data)

        self.data = self.data.replace('An Leas-Chathaoirleach:', '\nAn Leas-Chathaoirleach:')
        self.data = self.data.replace('----An Cathaoirleach:', '\nAn Cathaoirleach:')

        # would be handy to replace all "An Leas-Chathaoirleach:" with "\nAn Leas-Chathaoirleach:" so we can parse things easier really, sometimes they get merged into other words (and other common names)

        lines = self.data.split('\n')
        good_lines = []

        for line in lines:
            line = line.strip()
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
            line = line.strip()
            try:
                int(line)
                good_lines.append('[PAGEBREAK]')
            except (ValueError, IndexError):
                good_lines.append(line)

        self.data = '\n'.join(good_lines)

    @property
    def section_headers(self):
        if not self.loaded:
            self.load()

        lines = self.data.split('\n')
        header_lines = []
        for line in lines:
            if '��������������' in line:
                header_lines.append(line.replace('�', ''))

        clean_headers = []
        for header in header_lines:

            header = header.replace('\x08', '')
            if len(header.split()):
                if header.split()[-1].isnumeric():
                    header = ' '.join(header.split()[:-1])

            header = header.strip()
            if '\x08' in header:
                header = header[:header.index('\x08')].replace('\n', ' ')

            header = ' '.join(header.strip().split('\n')).strip()

            if header:
                try:
                    int(header[0])
                    datetime.datetime.strptime(header, '%d/%m/%YA%M%S0')
                except (ValueError, IndexError):
                    clean_headers.append(header)
        return clean_headers

    @property
    def date(self):
        return datetime.datetime.strptime(
            os.path.splitext(self.fp.split('_')[-1])[0],
            '%Y-%m-%d'
        )

    @property
    def debate_sections(self):
        if not self.loaded:
            self.load()
        from oireachtas_data.utils import window
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
