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
