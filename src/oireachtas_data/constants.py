import os
from importlib.metadata import version

BASE_DIR = (
    "/tmp/oireachtas_data"
    if os.getenv("TEST_ENV", "False") != "False"
    else os.path.expanduser(
        os.getenv(
            "OIREACHTAS_DATA_DIR",
            os.path.join(
                os.getenv("XDG_DATA_HOME", "~/.local/share"), "oireachtas_data"
            ),
        )
    )
)
os.makedirs(BASE_DIR, exist_ok=True)

OIREACHTAS_DIR = os.path.join(
    BASE_DIR,
    version("oireachtas-data").split(".")[0],
)
os.makedirs(OIREACHTAS_DIR, exist_ok=True)

MEMBERS_DIR = os.path.join(OIREACHTAS_DIR, "members")
