import datetime
from pathlib import Path

from oireachtas_data.models.debate import Debate
from oireachtas_data.models.debate_section import DebateSection
from oireachtas_data.models.para import Para
from oireachtas_data.models.speech import Speech


def test_debate_model_contains_archive_data_and_nested_models():
    paragraph = Para(eid="para_1", content="Hello world.")
    speech = Speech(by="#ExampleSpeaker", eid="spk_1", paras=[paragraph])
    section = DebateSection(show_as="Opening", speeches=[speech])
    pdf = Path("reports/debate.pdf")
    metadata = {"contextDate": "2026-10-22"}
    debate = Debate(
        date="2026-10-22",
        chamber="Dáil Éireann",
        debate_sections=[section],
        metadata=metadata,
        files={"pdf": pdf},
        uri="https://data.oireachtas.ie/debate/1",
        text="Hello world.",
    )

    assert debate.metadata is metadata
    assert debate.files["pdf"] == pdf
    assert debate.pdf_location == pdf
    assert debate.text == "Hello world."
    assert debate.timestamp == datetime.datetime(2026, 10, 22)
    assert debate.content_by_speaker["ExampleSpeaker"] == [paragraph]
    assert debate.serialize()["sections"][0]["speeches"][0]["paras"][0]["content"] == "Hello world."
