"""Tests for routes module"""
import json
import unittest

import paket_stellar
import util.logger
import webserver

import db
import routes
import tests

LOGGER = util.logger.logging.getLogger('pkt.funder.test')
util.logger.setup()
APP = webserver.setup(routes.BLUEPRINT)
APP.testing = True


class BaseRoutesTests(unittest.TestCase):
    """Base class for all routes tests."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = APP.test_client()
        self.host = 'http://localhost'
        LOGGER.info('init done')

    def setUp(self):
        tests.init_db()

    def call(self, path, expected_code=None, fail_message=None, seed=None, **kwargs):
        """Post data to API server."""
        LOGGER.info("calling %s", path)
        if seed:
            fingerprint = webserver.validation.generate_fingerprint(
                "{}/v{}/{}".format(self.host, routes.VERSION, path), kwargs)
            signature = webserver.validation.sign_fingerprint(fingerprint, seed)
            headers = {
                'Pubkey': paket_stellar.get_keypair(seed=seed).address().decode(),
                'Fingerprint': fingerprint, 'Signature': signature}
        else:
            headers = None
        response = self.app.post("/v{}/{}".format(routes.VERSION, path), headers=headers, data=kwargs)
        response = dict(real_status_code=response.status_code, **json.loads(response.data.decode()))
        if expected_code:
            self.assertEqual(response['real_status_code'], expected_code, "{} ({})".format(
                fail_message, response.get('error')))
        return response

    def internal_test_create_user(self, keypair, call_sign, **kwargs):
        """Create user"""
        pubkey = keypair.address().decode()
        seed = keypair.seed()
        user = self.call(
            'create_user', 201, 'could not create user', seed,
            user_pubkey=pubkey, call_sign=call_sign, **kwargs)['user']
        self.assertEqual(user['pubkey'], pubkey,
                         "pubkey of created user: {} does not match given: {}".format(user['pubkey'], pubkey))
        self.assertEqual(user['call_sign'], call_sign,
                         "call sign of created user: {} does not match given: {}".format(user['call_sign'], call_sign))
        return user


class CreateUserTest(BaseRoutesTests):
    """Test for create_user endpoint."""

    def test_create_user(self):
        """Test create user."""
        keypair = paket_stellar.get_keypair()
        call_sign = 'test_user'
        self.internal_test_create_user(keypair, call_sign)
        users = db.get_users()
        self.assertEqual(len(users), 1, "number of existing users: {} should be 1".format(len(users)))

    def test_invalid_call_sign(self):
        """Test create user with invalid call_sign"""
        keypair = paket_stellar.get_keypair()
        self.call(
            'create_user', 400, 'created user with invalid call_sign',
            seed=keypair.seed(), call_sign=keypair.address().decode())

    def test_create_with_infos(self):
        """Test create user with provided user info."""
        keypair = paket_stellar.get_keypair()
        call_sign = 'test_user'
        full_name = 'Kapitoshka Vodyanovych'
        phone_number = '+380 67 13 666'
        address = 'Vulychna 14, Trypillya'
        user = self.internal_test_create_user(
            keypair, call_sign, full_name=full_name, phone_number=phone_number, address=address)
        user_infos = db.get_user_infos(user['pubkey'])
        self.assertEqual(
            user_infos['full_name'], full_name,
            "stored full name: {} does not match given: {}".format(user_infos['full_name'], full_name))
        self.assertEqual(
            user_infos['phone_number'], phone_number,
            "stored phone number: {} does not match given: {}".format(user_infos['phone_number'], phone_number))
        self.assertEqual(
            user_infos['address'], address,
            "stored address: {} does not match given: {}".format(user_infos['address'], address))

    def test_non_unique_pubkey(self):
        """Test user creation on non uniq pubkey"""
        keypair = paket_stellar.get_keypair()
        call_sign = 'test_user'
        self.internal_test_create_user(keypair, call_sign)
        self.call(
            'create_user', 400, 'created user with non uniq pubkey', keypair.seed(),
            user_pubkey=keypair.address(), call_sign='another_call_sign')

    def test_non_unique_call_sign(self):
        """Test user creation on non unique call sign"""
        keypair = paket_stellar.get_keypair()
        call_sign = 'test_user'
        self.internal_test_create_user(keypair, call_sign)
        another_keypair = paket_stellar.get_keypair()
        self.call(
            'create_user', 400, 'created user with non uniq call sign', another_keypair.seed(),
            user_pubkey=another_keypair.address(), call_sign=call_sign)


class GetUserTest(BaseRoutesTests):
    """Test for get_user endpoint."""

    def test_get_user_by_pubkey(self):
        """Test get user by pubkey."""
        keypair = paket_stellar.get_keypair()
        call_sign = 'test_user'
        user = self.internal_test_create_user(keypair, call_sign)
        stored_user = self.call('get_user', 200, 'could not get user', pubkey=user['pubkey'])['user']
        self.assertEqual(
            stored_user['pubkey'], user['pubkey'], "stored user: {} does not match created one: {}".format(
                stored_user['pubkey'], user['pubkey']))

    def test_get_user_by_call_sign(self):
        """Test get user by call sign."""
        keypair = paket_stellar.get_keypair()
        call_sign = 'test_user'
        user = self.internal_test_create_user(keypair, call_sign)
        stored_user = self.call('get_user', 200, 'could not get user', call_sign=call_sign)['user']
        self.assertEqual(
            stored_user['call_sign'], user['call_sign'], "stored user: {} does not match created one: {}".format(
                stored_user['call_sign'], user['call_sign']))

    def test_get_non_existent_user(self):
        """Test get user on non existent publik key and call sign."""
        keypair = paket_stellar.get_keypair()
        self.internal_test_create_user(keypair, 'call_sign')
        self.call(
            'get_user', 404, 'does not get not found status code on non-existed pubkey',
            keypair.seed(), pubkey='public key')
        self.call(
            'get_user', 404, 'does not get not found status code on non-existed call sign',
            keypair.seed(), call_sign='another call sign')


class UserInfosTest(BaseRoutesTests):
    """Test for user_infos endpoint."""

    def test_with_user_creation(self):
        """Test for getting user infos."""
        keypair = paket_stellar.get_keypair()
        call_sign = 'test_user'
        full_name = 'Kapitoshka Vodyanovych'
        phone_number = '+380 67 13 666'
        address = 'Vulychna 14, Trypillya'
        self.internal_test_create_user(
            keypair, call_sign, full_name=full_name, phone_number=phone_number, address=address)
        user_infos = self.call(
            'user_infos', 200, 'could not get user infos',
            seed=keypair.seed(), user_pubkey=keypair.address())['user_details']
        self.assertEqual(
            user_infos['full_name'], full_name, "stored full name: {} does not match given: {}".format(
                user_infos['full_name'], full_name))
        self.assertEqual(
            user_infos['phone_number'], phone_number, "stored phone number: {} does not match given: {}".format(
                user_infos['phone_number'], phone_number))
        self.assertEqual(
            user_infos['address'], address, "stored address: {} does not match given: {}".format(
                user_infos['address'], address))

    def test_adding_portions(self):
        """Test for adding info by portions."""
        keypair = paket_stellar.get_keypair()
        call_sign = 'test_user'
        self.internal_test_create_user(keypair, call_sign)
        user_details = {
            'full_name': 'Kapitoshka Vodyanovych',
            'phone_number': '+380 67 13 666',
            'address': 'Vulychna 14, Trypillya'
        }
        passed_details = {}
        for key, value in user_details.items():
            stored_user_details = self.call(
                'user_infos', 200, "could not add new user's detail: {}={}".format(key, value),
                keypair.seed(), **{key: value})['user_details']
            passed_details[key] = value
            for detail_name, detail_value in passed_details.items():
                self.assertIn(
                    detail_name, stored_user_details, "user details does not contails new detail: {}={}".format(
                        detail_name, detail_value))
                self.assertEqual(
                    stored_user_details[detail_name],
                    detail_value, "new added detail: {} does not match given: {}".format(
                        stored_user_details[detail_name], detail_value))
                test_result = db.get_test_result(keypair.address().decode(), 'basic')
                self.assertEqual(
                    test_result, 1 if len(passed_details) == 3 else 0,
                    "got unexpected test result: {} for user with details: {}".format(
                        test_result, ''.join(["{}={}".format(key, value) for key, value in passed_details.items()])))


class PurchaseXlmTest(BaseRoutesTests):
    """Test for purchase_xlm endpoint."""

    def test_purchase(self):
        """Test for purchasing XLM."""
        keypair = paket_stellar.get_keypair()
        full_name = 'New Name'
        phone_number = '+48 045 237 27 36'
        address = 'New Address'
        self.internal_test_create_user(
            keypair, 'new_user', full_name=full_name, phone_number=phone_number, address=address)
        # need to add generated address checking
        self.call(
            'purchase_xlm', 201, 'could not purchase xlm', keypair.seed(),
            user_pubkey=keypair.address(), euro_cents=500, payment_currency='ETH')


class PurchaseBulTest(BaseRoutesTests):
    """Test for purchase_bul endpoint."""

    def test_purchase(self):
        """Test for purchasing BUL."""
        keypair = paket_stellar.get_keypair()
        full_name = 'New Name'
        phone_number = '+48 045 237 27 36'
        address = 'New Address'
        self.internal_test_create_user(
            keypair, 'new_user', full_name=full_name, phone_number=phone_number, address=address)
        # need to add generated address checking
        self.call(
            'purchase_bul', 201, 'could not purchase xlm', keypair.seed(),
            user_pubkey=keypair.address(), euro_cents=500, payment_currency='ETH')
