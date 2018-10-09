"""Tests for routines module"""
import unittest

import paket_stellar
import util.logger

import db
import routines
import tests

LOGGER = util.logger.logging.getLogger('pkt.funder.test')
USERS_NUMBER = 6
TIMEOUT = 360


def set_trust(pubkey, seed, limit=None):
    """Set trust limit for pubkey"""
    LOGGER.info("setting trust limit: %s for address: %s", limit, pubkey)
    prepared_transaction = routines.paket_stellar.prepare_trust(pubkey, limit)
    routines.paket_stellar.submit_transaction_envelope(prepared_transaction, seed)


class RoutinesTest(unittest.TestCase):
    """Test for routines"""

    def __init__(self, *args, **argv):
        super().__init__(*args, **argv)
        self.actual_keypairs = {}
        self.purchase_amount = db.MINIMUM_PAYMENT + 100
        self.half_purchase_amount = db.MINIMUM_PAYMENT / 2
        self.eth_full_payment = db.util.conversion.eth_to_wei(
            str(self.purchase_amount / 100 / float(db.prices.eth_price())))
        self.eth_half_payment = db.util.conversion.eth_to_wei(
            str(self.half_purchase_amount / 100 / float(db.prices.eth_price())))

    def setUp(self):
        """Clear table and refill them with new data"""
        tests.init_db()

        self.actual_keypairs.clear()
        LOGGER.info('generating new keypairs...')
        for number in range(USERS_NUMBER):
            new_keypair = paket_stellar.get_keypair()
            db.create_user(new_keypair.address(), 'callsign_{}'.format(number))
            if number % 2 == 0:
                LOGGER.info("creating account for address: %s", new_keypair.address())
                routines.create_new_account(new_keypair.address(), 50000000)
            db.set_internal_user_info(
                new_keypair.address(), full_name='Full Name', phone_number='+380991128370', address='address')
            self.actual_keypairs[new_keypair.address().decode()] = new_keypair.seed().decode()

    def test_check_purchases_addresses(self):
        """Test for check_purchases_addresses routine"""
        users = db.get_users()
        full_paid_addresses = [
            db.get_payment_address(users['callsign_0']['pubkey'], self.purchase_amount, 'ETH', 'XLM'),
            db.get_payment_address(users['callsign_1']['pubkey'], self.purchase_amount, 'ETH', 'BUL')
        ]
        half_paid_addresses = [
            db.get_payment_address(users['callsign_2']['pubkey'], self.purchase_amount, 'ETH', 'BUL'),
            db.get_payment_address(users['callsign_3']['pubkey'], self.purchase_amount, 'ETH', 'XLM')
        ]

        original_function = routines.get_balance
        routines.get_balance = lambda address, _: \
            self.eth_full_payment if address in full_paid_addresses else self.eth_half_payment

        routines.check_purchases_addresses()
        purchases = db.get_unpaid()
        self.assertNotEqual(len(purchases), 0)
        for purchase in purchases:
            if purchase['payment_pubkey'] in full_paid_addresses:
                self.assertEqual(purchase['paid'], 1,
                                 "purchase with full funded address %s has unpaid status" % purchase['payment_pubkey'])
            if (purchase['payment_pubkey'] not in full_paid_addresses or
                    purchase['payment_pubkey'] in half_paid_addresses):
                self.assertEqual(purchase['paid'], 0,
                                 "purchase without full funded address %s"
                                 "has wrong paid status: %s" % (purchase['payment_pubkey'], purchase['paid']))
        routines.get_balance = original_function

    def test_send_requested_currency(self):
        """Test for send_requested_currency"""
        users = db.get_users()
        successful_address = [
            db.get_payment_address(users['callsign_0']['pubkey'], self.purchase_amount, 'ETH', 'XLM'),
            db.get_payment_address(users['callsign_1']['pubkey'], self.purchase_amount, 'ETH', 'XLM'),
            db.get_payment_address(users['callsign_2']['pubkey'], self.purchase_amount, 'ETH', 'BUL')
        ]
        failed_address = [
            db.get_payment_address(users['callsign_3']['pubkey'], self.purchase_amount, 'ETH', 'BUL'),
            db.get_payment_address(users['callsign_4']['pubkey'], self.purchase_amount, 'ETH', 'BUL'),
            db.get_payment_address(users['callsign_5']['pubkey'], self.purchase_amount, 'ETH', 'BUL')
        ]
        routines.create_new_account(users['callsign_5']['pubkey'], 50000000)
        set_trust(users['callsign_5']['pubkey'], self.actual_keypairs[users['callsign_5']['pubkey']], 1000000)
        set_trust(users['callsign_2']['pubkey'], self.actual_keypairs[users['callsign_2']['pubkey']])

        original_function = routines.get_balance
        routines.get_balance = lambda address, _: self.eth_full_payment

        routines.check_purchases_addresses()
        routines.send_requested_currency()
        purchases = db.get_paid()
        self.assertEqual(len(purchases), 0)
        for purchase in db.get_purchases():
            if purchase['payment_pubkey'] in successful_address:
                self.assertEqual(purchase['paid'], 2, "purchase with address: {} has paid status: {} but expected: 2".
                                 format(purchase['payment_pubkey'], purchase['paid']))
            if purchase['payment_pubkey'] in failed_address:
                self.assertEqual(purchase['paid'], -1, "purchase with address: {} has paid status: {} but expected: -1".
                                 format(purchase['payment_pubkey'], purchase['paid']))
        routines.get_balance = original_function


class BalanceTest(unittest.TestCase):
    """Test getting balance for ETH/BTC addresses"""

# pylint: disable=no-self-use
    def test_btc_address(self):
        """Test balance with valid BTC address"""
        balance = routines.get_btc_balance('2N6WqqshyxoWuBGHLjbwnWAQSigJ4TJkYrt')
        self.assertGreater(balance, -1, "balance has wrong value: {}".format(balance))

    def test_invalid_btc_address(self):
        """Test balance with invalid BTC address"""
        with self.assertRaises(routines.BalanceError):
            routines.get_btc_balance('invalid_address')

    def test_eth_address(self):
        """Test balance with valid ETH address"""
        balance = routines.get_eth_balance('0xce85247b032f7528ba97396f7b17c76d5d034d2f')
        self.assertGreater(balance, -1, "balance has wrong value: {}".format(balance))

    def test_invalid_eth_address(self):
        """Test balance with invalid ETH address"""
        with self.assertRaises(routines.BalanceError):
            routines.get_eth_balance('invalid_address')
# pylint: enable=no-self-use
