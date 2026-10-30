"""Find suspicious duplicate report files or question records in an archive."""

import argparse
import hashlib
import json
import os
import re
from collections import defaultdict
from pathlib import Path

from oireachtas_data.constants import OIREACHTAS_DIR


CHUNK_SIZE = 64 * 1024


def _digest(path, sample=False):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        if sample:
            digest.update(handle.read(CHUNK_SIZE))
            if path.stat().st_size > CHUNK_SIZE:
                handle.seek(-CHUNK_SIZE, os.SEEK_END)
                digest.update(handle.read(CHUNK_SIZE))
        else:
            for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
                digest.update(chunk)
    return digest.digest()


def _candidates(root, all_files):
    for directory, subdirectories, filenames in os.walk(root):
        subdirectories.sort()
        for name in sorted(filenames):
            path = Path(directory) / name
            if not all_files and (
                "reports" not in path.relative_to(root).parts
                or path.suffix.lower() not in (".xml", ".pdf")
            ):
                continue
            if path.is_file() and not path.is_symlink():
                yield path


def _group_by_digest(paths, sample):
    groups = defaultdict(list)
    for path in paths:
        groups[_digest(path, sample)].append(path)
    return [group for group in groups.values() if len(group) > 1]


def find_duplicates(root, all_files=False, include_same_name=False):
    """Return (size, SHA-256 hex digest, paths) for suspicious exact copies.

    Report filenames contain a hash of their source URL, so identical names in
    different periods normally represent the same report. By default, only
    groups with distinct filenames are returned.
    """
    by_size = defaultdict(list)
    for path in _candidates(Path(root), all_files):
        by_size[path.stat().st_size].append(path)

    matches = []
    for size, paths in by_size.items():
        if len(paths) < 2:
            continue
        for sample_group in _group_by_digest(paths, sample=True):
            for group in _group_by_digest(sample_group, sample=False):
                if include_same_name or len({path.name for path in group}) > 1:
                    matches.append((size, _digest(group[0]).hex(), sorted(group)))
    return sorted(matches, key=lambda match: (-match[0], match[2][0]))


def _question_months(root):
    root = Path(root)
    questions = root / "questions" if (root / "questions").is_dir() else root
    if re.fullmatch(r"\d{4}-\d{2}", questions.name):
        return [questions]
    if (questions / "pages").is_dir():
        return [questions]
    return sorted(
        path for path in questions.iterdir()
        if re.fullmatch(r"\d{4}-\d{2}", path.name) and path.is_dir()
    )


def find_duplicate_questions(root):
    """Find distinct question URIs with the same date, asker, and question text."""
    matches = []
    for month in _question_months(root):
        by_question = defaultdict(list)
        pages = sorted(month.glob("*/pages/*.json")) + sorted(
            (month / "pages").glob("*.json")
        )
        for page in pages:
            for item in json.loads(page.read_text(encoding="utf-8"))["results"]:
                question = item.get("question") or {}
                uri = question.get("uri")
                date = question.get("date") or item.get("contextDate")
                asker = (question.get("by") or {}).get("memberCode")
                text = " ".join((question.get("showAs") or "").split())
                if not (uri and date and asker and text):
                    continue
                by_question[(date, asker, text)].append(
                    (
                        uri,
                        question.get("questionNumber"),
                        page,
                        " ".join((question.get("answerText") or "").split()),
                    )
                )
        for (date, asker, text), entries in by_question.items():
            if len({entry[0] for entry in entries}) > 1:
                # Overlapping downloads can store the same URI more than once.
                unique = {entry[0]: entry for entry in entries}
                matches.append((date, asker, text, sorted(unique.values())))
    return sorted(matches, key=lambda match: (match[0], match[1], match[2]))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "directory", nargs="?", type=Path, default=Path(OIREACHTAS_DIR) / "archive",
        help="archive directory to scan (default: configured Oireachtas archive)",
    )
    parser.add_argument(
        "--all-files", action="store_true", help="scan every file, including API JSON pages"
    )
    parser.add_argument(
        "--include-same-name", action="store_true",
        help="also report copies with the same URL-derived filename",
    )
    parser.add_argument(
        "--questions", action="store_true",
        help="find question records with the same date, asker, and text but different URIs",
    )
    args = parser.parse_args(argv)
    if not args.directory.is_dir():
        parser.error("directory does not exist: " + str(args.directory))
    if args.questions and (args.all_files or args.include_same_name):
        parser.error("--all-files and --include-same-name apply only to file checks")

    if args.questions:
        matches = find_duplicate_questions(args.directory)
        for date, asker, question_text, entries in matches:
            answers_match = len({entry[3] for entry in entries}) == 1
            print("%s  %s  %s  answers %s" % (
                date, asker, question_text[:160], "match" if answers_match else "differ"
            ))
            for uri, number, page, _ in entries:
                print("  %s  number=%s  page=%s" % (uri, number, page))
        print("%s suspicious duplicate question group(s)" % len(matches))
        return 1 if matches else 0

    matches = find_duplicates(args.directory, args.all_files, args.include_same_name)
    for size, digest, paths in matches:
        print("%s bytes  sha256:%s  %s files" % (size, digest, len(paths)))
        for path in paths:
            print("  " + str(path))
    print("%s suspicious duplicate group(s)" % len(matches))
    return 1 if matches else 0


if __name__ == "__main__":
    raise SystemExit(main())
