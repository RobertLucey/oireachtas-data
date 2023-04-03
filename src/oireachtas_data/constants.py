import os
import pkg_resources

BASE_DIR = (
    "/opt/oireachtas_data"
    if os.getenv("TEST_ENV", "False") == "False"
    else "/tmp/oireachtas_data"
)
os.makedirs(BASE_DIR, exist_ok=True)

OIREACHTAS_DIR = os.path.join(
    BASE_DIR,
    pkg_resources.require("oireachtas_data")[0].version.split(".")[0],
)
os.makedirs(OIREACHTAS_DIR, exist_ok=True)

DEBATES_DIR = os.path.join(OIREACHTAS_DIR, "debates")
os.makedirs(DEBATES_DIR, exist_ok=True)

MEMBERS_DIR = os.path.join(OIREACHTAS_DIR, "members")
os.makedirs(MEMBERS_DIR, exist_ok=True)

LOG_LOCATION = (
    "/var/log/oireachtas_data/oireachtas_data.log"
    if os.getenv("TEST_ENV", "False") == "False"
    else "/tmp/test_oireachtas_data.log"
)
