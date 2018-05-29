"""Run the PaKeT funding server."""
import sys
import os.path

import webserver
import funder.routes

# Python imports are silly.
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
# pylint: disable=wrong-import-position
import funder.swagger_specs
# pylint: enable=wrong-import-position

if len(sys.argv) == 2:
    FUNDER_PORT = sys.argv[1]
else:
    FUNDER_PORT = os.environ.get('PAKET_FUNDER_PORT', 5000)

webserver.run(funder.routes.BLUEPRINT, funder.swagger_specs.CONFIG, FUNDER_PORT)
