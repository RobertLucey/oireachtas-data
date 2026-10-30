import inspect
from unittest.mock import patch

from oireachtas_data.bin import load_all


def test_load_command_exposes_every_collection(tmp_path):
    archive = tmp_path / "archive"
    (archive / "members").mkdir(parents=True)

    frame_locals = {}

    def capture_frame():
        frame = inspect.currentframe().f_back
        while frame.f_code.co_name != "main":
            frame = frame.f_back
        frame_locals.update(frame.f_locals)

    with patch.object(load_all.pdb, "set_trace", side_effect=capture_frame) as prompt:
        load_all.main(["--archive-dir", str(archive)])

    prompt.assert_called_once()
    assert frame_locals["db"].root == archive
    for name in load_all.COLLECTIONS:
        assert frame_locals[name] is getattr(frame_locals["db"], name)
