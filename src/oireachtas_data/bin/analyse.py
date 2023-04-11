import argparse
import pprint
import os
from collections import Counter, defaultdict

from oireachtas_data.utils import get_debates, get_duplicate_sections_of_debate

from oireachtas_data import logger


def missing_debate_sections(debate):
    # This may be due to not being able to find in the pdf or that there's just no content that is present
    # TODO: give stats on section by count of missing
    data = defaultdict(list)
    empty_debate_sections = [
        section for section in debate.debate_sections if section.is_empty
    ]
    for section in empty_debate_sections:
        logger.warning(f"{debate.json_location}: {section.show_as}")
        data["missing_section_names"].append(section.show_as)
        data["location"].append(os.path.basename(debate.json_location))
    return data


def pdf_parsed_data(debate):
    # To go through and see if there's any weirdness since non pdf should be trusted

    data = defaultdict(list)
    from_pdf = [section for section in debate.debate_sections if section.is_from_pdf]
    for section in from_pdf:
        logger.warning(f"{debate.json_location}: {section.show_as}")
        data["section_names"].append(section.show_as)
        data["location"].append(os.path.basename(debate.json_location))
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--missing-debate-sections", dest="missing_debate_sections", action="store_true"
    )
    parser.add_argument(
        "--pdf-parsed-data", dest="pdf_parsed_data", action="store_true"
    )
    parser.add_argument(
        "--duplicate-sections", dest="duplicate_sections", action="store_true"
    )
    args = parser.parse_args()

    data = []
    debates = get_debates()
    for debate in debates:
        debate.load_data()

        # TODO: Check for duplicate debate sections in the same json file
        # TODO: The ratio diff between text from json and text from pdf, if we're missing a lot
        # What about duplicate debate secion names? Is that dangerous?

        if args.missing_debate_sections:
            debate_data = missing_debate_sections(debate)
            if debate_data:
                data.append(debate_data)
        elif args.pdf_parsed_data:
            debate_data = pdf_parsed_data(debate)
            if debate_data:
                data.append(debate_data)
        elif args.duplicate_sections:
            debate_data = get_duplicate_sections_of_debate(debate)
            if debate_data:
                data.append(debate_data)
        else:
            logger.error("Select something to analyse")

    # simple counts
    if args.missing_debate_sections or args.pdf_parsed_data:
        if data:
            for k in data[0].keys():
                print(k.title())
                print("=" * len(k))
                d = [d[k] for d in data]
                d = [item for sublist in d for item in sublist]
                pprint.pprint(Counter(d))


if __name__ == "__main__":
    main()
