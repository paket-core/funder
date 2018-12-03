"""Tests for db module"""
import unittest

import util.logger

import db
import tests

LOGGER = util.logger.logging.getLogger('pkt.funder.test')


class DBTest(unittest.TestCase):
    """Testing the database module."""

    def setUp(self):
        tests.init_db()

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
        with self.assertRaises(db.UnknownUser) as exception_context:
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
        phone_number, address = '+380982348561', 'asdf'
        self.internal_test_create_user(pubkey, call_sign)
        db.set_internal_user_info(pubkey, phone_number=phone_number)
        self.assertEqual(db.get_user_infos(pubkey)['phone_number'], phone_number)
        phone_number = '+380962358161'
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

    def test_monthly_expenses(self):
        """Test monthly expanses logic"""
        pubkey, call_sign = 'pubkey', 'call_sign'
        self.internal_test_create_user(pubkey, call_sign)
        monthly_expenses = db.get_monthly_expenses(pubkey)
        self.assertEqual(monthly_expenses, 0, 'monthly expenses are incorrect')
        db.update_test(pubkey, 'basic', 1)
        payment_address = db.get_payment_address(pubkey, 500, 'BTC', 'BUL')
        db.set_purchase(pubkey, payment_address, 'BTC', 500, 'BUL', 2)
        monthly_expenses = db.get_monthly_expenses(pubkey)
        self.assertEqual(monthly_expenses, 500, 'monthly expenses are incorrect')
        payment_address = db.get_payment_address(pubkey, 600, 'ETH', 'XLM')
        db.set_purchase(pubkey, payment_address, 'ETH', 500, 'XLM', 1)
        monthly_expenses = db.get_monthly_expenses(pubkey)
        self.assertEqual(monthly_expenses, 1100, 'monthly expenses are incorrect')

    def test_get_payment_address(self):
        """Test get payment address"""
        pubkey, call_sign = 'pubkey', 'call_sign'
        self.internal_test_create_user(pubkey, call_sign)
        db.update_test('pubkey', 'basic', 1)
        payment_address = db.get_payment_address(pubkey, 500, 'BTC', 'BUL')
        purchase = db.get_unpaid_purchases()[0]
        self.assertEqual(payment_address, purchase['payment_pubkey'], 'payment address was not created for user')
        self.assertEqual(pubkey, purchase['user_pubkey'], 'payment address was created for another user')
        self.assertEqual(500, purchase['euro_cents'], 'created record has wrong euro_cents value')
        self.assertEqual('BTC', purchase['payment_currency'], 'created record has wrong payment_currency value')
        self.assertEqual('BUL', purchase['requested_currency'], 'created record has wrong requested_currency value')

    def test_get_unpaid(self):
        """Test get unpaid purchases"""
        pubkey, call_sign = 'pubkey', 'call_sign'
        self.internal_test_create_user(pubkey, call_sign)
        db.update_test(pubkey, 'basic', 1)
        purchase_amount = 5
        payment_addresses = [db.get_payment_address(pubkey, 700, 'BTC', 'XLM') for _ in range(purchase_amount)]
        unpaid = db.get_unpaid_purchases()
        self.assertEqual(len(unpaid), purchase_amount, 'actual purchases amount does not correspond to control value')
        for address in payment_addresses:
            with self.subTest():
                self.assertIn(address, (purchase['payment_pubkey'] for purchase in unpaid),
                              'created payment address does not present among unpaid purchases')

    def test_get_paid(self):
        """Test get paid purchases"""
        pubkey, call_sign = 'pubkey', 'call_sign'
        self.internal_test_create_user(pubkey, call_sign)
        db.update_test(pubkey, 'basic', 1)
        purchase_amount = 5
        payment_addresses = [db.get_payment_address(pubkey, 700, 'BTC', 'XLM') for _ in range(purchase_amount)]
        for address in payment_addresses:
            db.set_purchase(pubkey, address, 'BTC', 700, 'XLM', 1)
        paid = db.get_paid_purchases()
        self.assertEqual(len(paid), purchase_amount, 'actual purchases amount does not correspond to control value')
        for address in payment_addresses:
            with self.subTest():
                self.assertIn(address, (purchase['payment_pubkey'] for purchase in paid),
                              'created payment address does not present among unpaid purchases')

    def test_update_purchase(self):
        """Test purchase updating."""
        pubkey, call_sign = 'pubkey', 'call_sign'
        self.internal_test_create_user(pubkey, call_sign)
        db.update_test(pubkey, 'basic', 1)
        address = db.get_payment_address(pubkey, 700, 'BTC', 'XLM')
        db.set_purchase(pubkey, address, 'BTC', 700, 'XLM', 1)
        purchase = db.get_paid_purchases()[0]
        self.assertEqual(purchase['paid'], 1, 'purchase does not updated')
