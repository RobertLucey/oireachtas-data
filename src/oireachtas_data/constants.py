import os
import pkg_resources

OIREACHTAS_DIR = os.path.join(
    '/opt/oireachtas_data',
    pkg_resources.require('oireachtas_data')[0].version.split('.')[0]
)
