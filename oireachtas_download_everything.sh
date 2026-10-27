#!/bin/sh
set -eu

cd "$(dirname "$0")"
sudo apt-get update
sudo apt-get install -y python3-venv python3-dev build-essential
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/oireachtas_download
.venv/bin/oireachtas_load_debates
