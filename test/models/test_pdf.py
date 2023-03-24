import os

from unittest import TestCase, skip

from oireachtas_data.models.new_pdf import PDF as NewPDF
from oireachtas_data.models.old_pdf import PDF as OldPDF
from oireachtas_data.models.pdf import to_text, pdf_parser_get


class PDFTest(TestCase):
    def setUp(self):
        self.resources_path = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "test/resources/",
        )

        self.resources_pdf_path = os.path.join(self.resources_path, "pdfs")
        self.resources_json_path = os.path.join(self.resources_path, "json")

    def test_parser_get(self):
        self.assertEqual(
            pdf_parser_get(
                os.path.join(
                    self.resources_pdf_path, "debate_Dáil Éireann_2021-12-02.pdf"
                )
            ),
            NewPDF,
        )
        self.assertEqual(
            pdf_parser_get(
                os.path.join(
                    self.resources_pdf_path, "debate_Dáil Éireann_2012-06-06.pdf"
                )
            ),
            OldPDF,
        )

    def test_to_text(self):
        text = to_text(
            os.path.join(self.resources_pdf_path, "debate_Dáil Éireann_2021-12-02.pdf")
        )
        self.assertLess(len(text), 550000)
        self.assertGreater(len(text), 500000)
