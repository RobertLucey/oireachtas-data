import argparse
import pprint
from collections import Counter, defaultdict

from oireachtas_data.archive import DownloadedDebates
from oireachtas_data.utils import get_duplicate_sections_of_debate

from oireachtas_data import logger


def missing_debate_sections(debate):
    # Report sections with no speakers or speeches.
    # TODO: give stats on section by count of missing
    data = defaultdict(list)
    empty_debate_sections = [
        section for section in debate.debate_sections if section.is_empty
    ]
    for section in empty_debate_sections:
        logger.warning(f"{debate.uri or debate.date}: {section.show_as}")
        data["missing_section_names"].append(section.show_as)
        data["location"].append(debate.date)
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--missing-debate-sections", dest="missing_debate_sections", action="store_true"
    )
    parser.add_argument(
        "--duplicate-sections", dest="duplicate_sections", action="store_true"
    )
    args = parser.parse_args()

    data = []
    debates = DownloadedDebates()
    for debate in debates:
        if args.missing_debate_sections:
            debate_data = missing_debate_sections(debate)
            if debate_data:
                data.append(debate_data)
        elif args.duplicate_sections:
            debate_data = get_duplicate_sections_of_debate(debate)
            if debate_data:
                data.append(debate_data)
        else:
            logger.error("Select something to analyse")

    # simple counts
    if args.missing_debate_sections:
        if data:
            for k in data[0].keys():
                print(k.title())
                print("=" * len(k))
                d = [d[k] for d in data]
                d = [item for sublist in d for item in sublist]
                pprint.pprint(Counter(d))


if __name__ == "__main__":
    main()
