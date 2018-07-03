"""Tests for db module"""
import unittest

import util.logger

import db

LOGGER = util.logger.logging.getLogger('pkt.funder.test')
util.logger.setup()


class DBTest(unittest.TestCase):
    """Testing the database module."""

    @classmethod
    def setUpClass(cls):
        """Create tables if they does not exists"""
        try:
            LOGGER.info('creating tables...')
            db.init_db()
        except db.util.db.mysql.connector.ProgrammingError:
            LOGGER.info('tables already exists')

    def setUp(self):
        assert db.DB_NAME.startswith('test'), "refusing to test on db named {}".format(db.DB_NAME)
        LOGGER.info('clearing database')
        db.util.db.clear_tables(db.SQL_CONNECTION, db.DB_NAME)

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
        with self.assertRaises(db.UserNotFound) as exception_context:
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

    def test_user_test_results(self):
        """Test adding, modifying, and reading test results"""
        pubkey, call_sign = 'pubkey', 'call_sign'
        self.internal_test_create_user(pubkey, call_sign)
        test_result = db.get_test_result(pubkey, 'basic')
        self.assertEqual(test_result, 0, 'newly created user already has result for test')
        db.update_test(pubkey, 'basic')
        test_result = db.get_test_result(pubkey, 'basic')
        self.assertEqual(test_result, None, 'updating test for user sets wrong result')
        db.update_test(pubkey, 'basic', 1)
        test_result = db.get_test_result(pubkey, 'basic')
        self.assertEqual(test_result, 1, 'reading test results does not return actual result')

    def test_monthly_allowance(self):
        """Test monthly allowance logic"""
        pubkey, call_sign = 'pubkey', 'call_sign'
        self.internal_test_create_user(pubkey, call_sign)
        monthly_allowance = db.get_monthly_allowance(pubkey)
        self.assertEqual(monthly_allowance, 0, 'newly created user has non-zero allowance')
        db.update_test(pubkey, 'basic', 1)
        monthly_allowance = db.get_monthly_allowance(pubkey)
        self.assertEqual(monthly_allowance, db.BASIC_MONTHLY_ALLOWANCE, 'test completeed user has wrong allowance')
