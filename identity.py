#!/usr/bin/env python3
"""Identity server for the PaKeT project."""
import flasgger
import flask

import logger
import webserver
import webserver.validation

import swagger_spec

logger.setup()
LOGGER = logger.logging.getLogger('pkt.identity')

VERSION = swagger_spec.CONFIG['info']['version']
BLUEPRINT = flask.Blueprint('identity', __name__)

# pylint: disable=missing-docstring
# See documentation in swagger_spec.


@BLUEPRINT.route("/v{}/test".format(VERSION), methods=['GET'])
@flasgger.swag_from(swagger_spec.TEST)
@webserver.validation.call
def test_handler():
    return {'status': 200, 'message': 'This is indeed a test.'}


if __name__ == '__main__':
    webserver.run(BLUEPRINT, swagger_spec.CONFIG, True)
