"""Tests for routes module"""
import json
import unittest

import paket_stellar
import util.logger
import webserver

import db
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


class RoutesTest(BaseRoutesTests):
    """Test for routes"""

    def test_create_user(self):
        """Test create user"""
        keypair = paket_stellar.get_keypair()
        pubkey = keypair.address().decode()
        call_sign = 'test_user'
        user = self.call('create_user', 200, 'could not create user', user_pubkey=pubkey, call_sign=call_sign)
        self.assertEqual(user['user_pubkey'], pubkey, '')
        users = db.get_users()
        self.assertEqual(len(users), 1, '')
        self.assertEqual(user['user_pubkey'], users[0]['user_pubkey'], '')
        self.assertEqual(user['call_sign'], users[0]['call_sign'])

    def test_create_with_infos(self):
        """Test create user with provided user info"""
        keypair = paket_stellar.get_keypair()
        pubkey = keypair.address().decode()
        call_sign = 'test_user'
        full_name = 'Kapitoshka Vodyanovych'
        phone_number = '+380 67 13 666'
        address = 'Vulychna 14, Trypillya'
        user = self.call('create_user', 200, 'could not create user', user_pubkey=pubkey,
                         call_sign=call_sign, full_name=full_name, phone_number=phone_number, address=address)
        self.assertEqual(user['user_pubkey'], pubkey, '')
        user_infos = db.get_user_infos(pubkey)
        self.assertEqual(user_infos['full_name'], full_name, '')
        self.assertEqual(user_infos['phone_number'], phone_number, '')
        self.assertEqual(user_infos['address'], address, '')
