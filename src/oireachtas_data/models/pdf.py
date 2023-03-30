import os

from oireachtas_data.models.new_pdf import PDF as NEW_PDF
from oireachtas_data.models.old_pdf import PDF as OLD_PDF

from oireachtas_data import logger


def to_text(fp):
    text_file = fp + ".txt"

    if not os.path.exists(text_file):
        with open(fp, "rb") as f:
            os.system(f"pdftotext '{fp}' '{text_file}'")

    if not os.path.exists(text_file):
        logger.error("Could not convert pdf to text: %s" % (text_file))
        return

    f = open(text_file, "r")
    data = f.read()
    f.close()

    return data


def pdf_parser_get(pdf_location):
    content = to_text(pdf_location)

    if content is None:
        logger.error("Could not parse pdf type: %s" % (pdf_location))
        return

    if "��������������" in content:
        return NEW_PDF
    return OLD_PDF
