"""Run the identity server."""
import sys
import os.path

import webserver

# Python imports are silly.
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
# pylint: disable=wrong-import-position
import identity
import identity.swagger_specs
# pylint: enable=wrong-import-position

if len(sys.argv) == 2:
    IDENTITY_PORT = sys.argv[1]
else:
    IDENTITY_PORT = os.environ.get('PAKET_IDENTITY_PORT', 5000)

webserver.run(identity.BLUEPRINT, identity.swagger_specs.CONFIG, IDENTITY_PORT)
