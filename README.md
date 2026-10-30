Oireachtas Data
===============

Download Oireachtas (Irish parliament) records and explore them locally.

Install & download
-------------------

Install [just](https://just.systems/) and run these commands from the repository:

```sh
git clone https://github.com/RobertLucey/oireachtas-data.git
cd oireachtas-data
just install
just download
```

`just` lists the available recipes. Downloads go to `data/oireachtas` by default;
set `OIREACHTAS_DATA_DIR` to use another location. The downloader saves members,
houses, parties, constituencies, debates, questions, votes, and legislation,
plus linked XML/PDF reports. It resumes on reruns and only re-fetches the
current month/year unless you pass `--refresh`:

```sh
just download --collections questions debates --workers 8
just download --refresh
```

Set `OIREACHTAS_ARCHIVE_DIR` to inspect an archive other than the default
`data/oireachtas/0/archive`.

Check for identical downloaded reports saved under different URL-derived names:

```sh
just duplicate-files
```

The check reads report XML and PDFs without changing them. It groups files by
size, compares short samples, then hashes matching candidates to confirm exact
copies. Copies with the same filename are skipped by default because that name
comes from the source URL; use `--include-same-name` to show them too. Use
`--all-files` to include API pages and other files. Exit status is 1 when it
finds suspicious groups, 0 when it finds none, and 2 for an invalid directory.

To check question metadata for repeated questions with different URIs, run:

```sh
just duplicate-questions
```

This groups records by date, asking member, and normalized question text. It
shows whether the answers match and where each record appears in the saved API
pages. It only reports matches; it does not remove records.

Explore interactively
----------------------

```sh
just load
```

Drops you into `pdb` with `db` and each collection (`members`, `houses`, `parties`, `constituencies`, `debates`, `questions`, `votes`, `bills`) ready to use, e.g. `p questions.filter(date="2024-01-22").first()`.

Query from Python
------------------

```python
from oireachtas_data.orm import OireachtasArchive

db = OireachtasArchive()

question = db.questions.filter(date="2024-01-22").first()
print(question.text, question.answer_text, question.by.member)

debate = db.debates.filter(date="2024-01-22").first()
print(debate.debate_sections[0].content)

bill = db.bills.filter(year=2024, status="Current").first()
print(bill.title, [v.pdf for v in bill.versions if v.pdf])
```

Every collection supports `.filter(...)`, `.first()`, `.get(...)`, and `.count()`. Filters match exactly by default; add `__contains` or `__in` for partial/set matches (`text__contains="housing"`). Nested fields work too (`by__member_code=...`). Each object's raw API payload is on `.metadata`.

Run tests with `just install-dev` and `just test`. You can pass pytest arguments,
for example `just test -q test/test_orm.py`.
