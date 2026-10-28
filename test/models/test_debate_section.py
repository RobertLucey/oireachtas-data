from oireachtas_data.models.debate_section import DebateSection
from oireachtas_data.models.para import Para
from oireachtas_data.models.speech import Speech


def test_section_serializes_and_searches_speeches():
    speech = Speech(by="#ExampleSpeaker", paras=[Para(content="Hello world.")])
    section = DebateSection(show_as="  Opening  ", speeches=[speech])

    assert section.show_as == "Opening"
    assert section.computed_speakers == {"ExampleSpeaker"}
    assert section.speech_contains("hello world", case_sensitive=False)
    assert not section.speech_contains("hello world")
    assert not section.is_empty
    assert section.serialize()["speeches"][0]["paras"][0]["content"] == "Hello world."
