Oireachtas Data
===============

Tools to download Oireachtas member records and debate reports, and explore the downloaded data.

Installation
------------

```sh
export OIREACHTAS_DATA_DIR="$PWD/data/oireachtas"
bash oireachtas_download_everything.sh
```

The full archive can be large and slow to download. Re-run the script to resume.

Usage
-----

Use the package commands to download all members and debates, then explore them:

```sh
export OIREACHTAS_DATA_DIR="$PWD/data/oireachtas"
oireachtas_download
oireachtas_load_debates
```

In Python, use the same archive and model objects:

```python
from oireachtas_data.archive import DownloadedDebates

debates = DownloadedDebates()
debate = debates[0]  # Debate containing DebateSection, Speech, and Para objects
print(debate.date, debate.debate_sections[0].show_as)
```

Early reports can contain summaries instead of speeches. Read them through `debate.debate_sections[0].summaries`, or use the section's `content` for its text.
