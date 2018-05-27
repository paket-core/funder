"""Test Funder."""
import os
import unittest

import identitymind
import db

LOGGER = identitymind.LOGGER


def print_result(kyc_result):
    """Print IdentityMind results."""
    LOGGER.debug(kyc_result)
    for field in ['tid', 'user', 'res', 'rcd', 'state', 'ednaScoreCard']:
        LOGGER.info("%s: %s", field, kyc_result.get(field))


class IdentityMindTest(unittest.TestCase):
    """Test IdentityMind."""

    def test_playing(self):
        """Test playing around."""
        kyc_post = identitymind.request_kyc(man='man', bfn="Tom", bsn="1520", profile='new', bco='USA', sco='USA')
        print_result(kyc_post)
        self.assertEqual(kyc_post['state'], 'A')

    def test_current_reputation(self):
        """
        check the `user` field. Can be managed in sandbox via the `bfn` parameter.
        """
        for val, resp in [
                ('Tom', 'TRUSTED'),
                ('Sue', 'SUSPICIOUS'),
                ('Brad', 'BAD'),
                ('someone', 'UNKNOWN')
        ]:
            LOGGER.warning("man='man called %s', bfn=val, bln='ed'", val)
            kyc_request = identitymind.request_kyc(man='man called {}'.format(val), bfn=val, bln="ed")
            print_result(kyc_request)
            self.assertEqual(kyc_request['user'], resp)

    def test_policy_result(self):
        """
        check the `state` field. Can be managed in sandbox via the `bc` parameter.
        """
        for val, resp in [
                ('Detroit', 'D'),
                ('Monte Rio', 'R'),
                ('someone', 'A')
        ]:
            kyc_request = identitymind.request_kyc(man='man from {}'.format(val), bc=val)
            print_result(kyc_request)
            self.assertEqual(kyc_request['state'], resp)


LOGGER = db.LOGGER
db.DB_NAME = 'test.db'

class DBTest(unittest.TestCase):
    """Testing the database module."""

    def setUp(self):
        LOGGER.info('setting up')
        try:
            os.unlink(db.DB_NAME)
        except FileNotFoundError:
            pass
        db.init_db()

    def tearDown(self):
        LOGGER.info('tearing down')
        try:
            os.unlink(db.DB_NAME)
        except FileNotFoundError:
            pass

    def test_get_user_args(self):
        """Test get_user arguments logic."""
        with self.assertRaises(AssertionError) as exception_context:
            db.get_user()
        self.assertEqual(
            str(exception_context.exception), 'specify either pubkey or call_sign',
            'called get_user with no arguments')
        with self.assertRaises(AssertionError) as exception_context:
            db.get_user('foo', 'bar')
        self.assertEqual(
            str(exception_context.exception), 'specify either pubkey or call_sign',
            'called get_user with two arguments')

    def internal_test_nonexistent(self, pubkey):
        """Test a non existing user."""
        with self.assertRaises(AssertionError) as exception_context:
            db.get_user(pubkey)
        self.assertEqual(
            str(exception_context.exception), "user with pubkey {} does not exists".format(pubkey),
            'called get_user with nonexisting user')

    def internal_test_create_user(self, pubkey, call_sign):
        """Test creating a user."""
        self.internal_test_nonexistent(pubkey)
        db.create_user(pubkey, call_sign)
        user = db.get_user(pubkey=pubkey)
        self.assertEqual(user['call_sign'], call_sign)
        user = db.get_user(call_sign=call_sign)
        self.assertEqual(user['pubkey'], pubkey)

    def test_internal_user_info(self):
        """Test adding, modifying, and reading internal user info."""
        pubkey, call_sign = 'pubkey', 'call_sign'
        phone_number, address = '1234', 'asdf'
        self.internal_test_create_user(pubkey, call_sign)
        db.set_internal_user_info(pubkey, phone_number=phone_number)
        self.assertEqual(db.get_user_infos(pubkey)['phone_number'], phone_number)
        phone_number = phone_number[::-1]
        db.set_internal_user_info(pubkey, phone_number=phone_number, address=address)
        self.assertEqual(db.get_user_infos(pubkey)['phone_number'], phone_number)
        self.assertEqual(db.get_user_infos(pubkey)['address'], address)


if __name__ == '__main__':
    unittest.main()
