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

webserver.run(funder.routes.BLUEPRINT, funder.swagger_specs.CONFIG, funder.routes.PORT)
