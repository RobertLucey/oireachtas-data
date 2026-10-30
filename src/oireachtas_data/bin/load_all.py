"""Explore every collection in a downloaded Oireachtas archive."""

# Collection locals are exposed at the Pdb prompt.
# ruff: noqa: F841

import argparse
import bdb
import logging
import pdb
import sys
from pathlib import Path

from oireachtas_data.orm import OireachtasArchive


COLLECTIONS = (
    "members",
    "houses",
    "parties",
    "constituencies",
    "debates",
    "questions",
    "votes",
    "bills",
)
LOG = logging.getLogger(__name__)


def main(argv=None):
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s", stream=sys.stdout)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-dir", type=Path, help="Local archive directory")
    args = parser.parse_args(argv)

    db = OireachtasArchive(args.archive_dir)
    if not db.root.is_dir() or not any(db.root.iterdir()):
        parser.error("No downloaded archive found at " + str(db.root))

    members = db.members
    houses = db.houses
    parties = db.parties
    constituencies = db.constituencies
    debates = db.debates
    questions = db.questions
    votes = db.votes
    bills = db.bills
    LOG.info("Local archive: %s", db.root.resolve())
    LOG.info("Available: db, %s", ", ".join(COLLECTIONS))
    LOG.info("Try: p questions.filter(date='2024-01-22').first()")
    LOG.info("Type q to exit.")
    try:
        pdb.set_trace()
        pass
    except bdb.BdbQuit:
        return


if __name__ == "__main__":
    main()
