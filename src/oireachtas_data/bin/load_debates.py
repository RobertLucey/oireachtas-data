import argparse
import bdb

from oireachtas_data.archive import DownloadedDebates


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive-dir", help="Archive written by oireachtas_download")
    args = parser.parse_args()
    debates = DownloadedDebates(args.archive_dir)

    print("Loaded %s debates" % len(debates))
    if not debates:
        print("No downloaded debates found. Run oireachtas_download first.")
        return
    print(
        "At the (Pdb) prompt, debates contains the downloaded records.\n"
        "Each debate has debate_sections containing Speech and Para models.\n"
        "Try:\n"
        "  debate = debates[0]\n"
        "  debate.date\n"
        "  debate.debate_sections\n"
        "  debate.pdf_location\n"
        "To find a paragraph and inspect its text and tokens:\n"
        "  para = next(p for d in debates for section in d.debate_sections "
        "for speech in section.speeches for p in speech.paras)\n"
        "  para.content\n"
        "  para.words[:10]\n"
        "  para.tokens[:10]\n"
        "Type q to exit."
    )

    import pdb

    try:
        pdb.set_trace()
        pass
    except bdb.BdbQuit:
        return


if __name__ == "__main__":
    main()
