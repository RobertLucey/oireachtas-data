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
