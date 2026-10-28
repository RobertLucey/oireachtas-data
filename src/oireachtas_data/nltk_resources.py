"""Load NLTK models only when text analysis needs them."""

import os
import stat
import tempfile
from functools import lru_cache
from pathlib import Path

import nltk


@lru_cache(maxsize=1)
def private_data_dir():
    configured = os.getenv("OIREACHTAS_NLTK_DATA_DIR")
    if configured:
        directory = Path(configured).expanduser()
    elif os.getenv("TEST_ENV", "False") != "False":
        directory = Path(tempfile.gettempdir()) / (
            "oireachtas_nltk_data_" + str(os.getuid())
        )
    else:
        directory = Path.home() / ".oireachtas_nltk_data"

    previous_umask = os.umask(0o077)
    try:
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    finally:
        os.umask(previous_umask)

    info = directory.stat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise PermissionError(
            "NLTK data directory must be owned by you and private: " + str(directory)
        )
    if str(directory) not in nltk.data.path:
        nltk.data.path.insert(0, str(directory))
    return directory


@lru_cache(maxsize=None)
def ensure_resource(package, resource):
    directory = private_data_dir()
    try:
        nltk.data.find(resource, paths=[str(directory)])
    except LookupError:
        if not nltk.download(package, download_dir=str(directory), quiet=True):
            raise LookupError("Could not download NLTK resource " + package)
        nltk.data.find(resource, paths=[str(directory)])
