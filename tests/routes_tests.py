"""Tests for routes module"""
import json
import unittest

import util.logger
import webserver

import routes

LOGGER = util.logger.logging.getLogger('pkt.funder.test')
util.logger.setup()
APP = webserver.setup(routes.BLUEPRINT)
APP.testing = True


class BaseRoutesTests(unittest.TestCase):
    """Base class for all routes tests"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = APP.test_client()
        self.host = 'http://localhost'
        LOGGER.info('init done')

    def call(self, path, expected_code=None, fail_message=None, **kwargs):
        """Post data to API server."""
        LOGGER.info("calling %s", path)
        response = self.app.post("/v{}/{}".format(routes.VERSION, path), data=kwargs)
        response = dict(real_status_code=response.status_code, **json.loads(response.data.decode()))
        if expected_code:
            self.assertEqual(response['real_status_code'], expected_code, "{} ({})".format(
                fail_message, response.get('error')))
        return response


class RoutesTest(unittest.TestCase):
    """Test for routes"""
