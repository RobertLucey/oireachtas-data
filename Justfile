# Run `just` to list recipes. Override OIREACHTAS_DATA_DIR or
# OIREACHTAS_ARCHIVE_DIR in the environment when using another archive.
set default-list := true
set positional-arguments

export OIREACHTAS_DATA_DIR := env('OIREACHTAS_DATA_DIR', justfile_directory() + '/data/oireachtas')
archive_dir := env('OIREACHTAS_ARCHIVE_DIR', OIREACHTAS_DATA_DIR + '/0/archive')

# Create the virtual environment and install the project.
install:
    python3 -m venv .venv
    .venv/bin/python -m pip install -e .

# Install the project and its test dependencies.
install-dev:
    python3 -m venv .venv
    .venv/bin/python -m pip install -e '.[dev]'

# Download all collections, or pass downloader options (for example --collections questions).
download *args:
    .venv/bin/oireachtas_download "$@"

# Explore the saved collections in pdb.
load:
    .venv/bin/oireachtas_load --archive-dir "{{archive_dir}}"

# Report identical XML/PDF files under different URL-derived names.
duplicate-files *args:
    .venv/bin/oireachtas_duplicates "{{archive_dir}}" "$@"

# Report question records with matching date, asker, and text but different URIs.
duplicate-questions:
    .venv/bin/oireachtas_duplicates --questions "{{archive_dir}}"

# Run the test suite, optionally passing pytest arguments.
test *args:
    .venv/bin/python -m pytest "$@"
