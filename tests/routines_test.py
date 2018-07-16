"""Tests for routines module"""
import unittest
import web3
import eth_utils

import paket_stellar
import util.logger

import db
import routines

LOGGER = util.logger.logging.getLogger('pkt.funder.test')
USERS_NUMBER = 6
TIMEOUT = 360


class RoutinesTest(unittest.TestCase):
    """Test for routines"""

    def __init__(self, *args, **argv):
        super().__init__(*args, **argv)
        self.eth_funder_seed = '4cdd30299b14203ba2289d6706acbf5e093fce6e170a48f3621c28d38f4ed20d'
        self.eth_node = 'https://ropsten.infura.io/9S2cUwgCk4jYKYG85rxJ'
        self.actual_keypairs = {}

    def setUp(self):
        """Clear table and refill them with new data"""
        try:
            LOGGER.info('creating tables...')
            db.init_db()
        except db.util.db.mysql.connector.ProgrammingError:
            LOGGER.info('tables already exists')
        db.util.db.clear_tables(db.SQL_CONNECTION, db.DB_NAME)

        self.actual_keypairs.clear()
        for number in range(USERS_NUMBER):
            new_keypair = paket_stellar.get_keypair()
            db.create_user(new_keypair.address(), 'callsign_{}'.format(number))
            if number % 2 == 0:
                routines.create_new_account(new_keypair.address(), 50000000)
            db.set_internal_user_info(new_keypair.address(),
                                      full_name='Full Name', phone_number='+4134976443', address='address')
            self.actual_keypairs[new_keypair.address().decode()] = new_keypair.seed().decode()

    def purchase(self, payment_address, amount, network):
        """Send amount of coins to specified address"""
        assert network == 'ETH', 'only ETH available for purchasing now'
        # pylint: disable=no-value-for-parameter,no-member
        account = web3.Account.privateKeyToAccount(self.eth_funder_seed)
        web3_api = web3.Web3(web3.HTTPProvider(self.eth_node))
        nonce = web3_api.eth.getTransactionCount(account.address)
        transaction = {
            'to': eth_utils.to_checksum_address(payment_address),
            'gas': 90000,
            'gasPrice': web3.Web3.toWei(5, 'gwei'),
            'value': amount,
            'nonce': nonce,
            'chainId': 3
        }
        signed = account.signTransaction(transaction)
        transaction_hash = web3_api.eth.sendRawTransaction(signed.rawTransaction)
        try:
            web3_api.eth.waitForTransactionReceipt(transaction_hash, TIMEOUT)
            return True
        except web3.utils.threads.Timeout:
            return False
        # pylint: enable=no-value-for-parameter,no-member

    def set_trust(self, pubkey, seed, limit=None):
        """Set trust limit for pubkey"""
        prepared_transaction = routines.paket_stellar.prepare_trust(pubkey, limit)
        routines.paket_stellar.submit_transaction_envelope(prepared_transaction, seed)

    def test_check_purchases_addresses(self):
        """Test for check_purchases_addresses routine"""
        users = db.get_users()
        full_paid_addresses = [
            db.get_payment_address(users['callsign_0']['pubkey'], 500, 'ETH', 'XLM'),
            db.get_payment_address(users['callsign_1']['pubkey'], 500, 'ETH', 'BUL')
        ]
        half_paid_addresses = [
            db.get_payment_address(users['callsign_2']['pubkey'], 500, 'ETH', 'BUL'),
            db.get_payment_address(users['callsign_3']['pubkey'], 500, 'ETH', 'XLM')
        ]
        for address in full_paid_addresses:
            self.purchase(address, 15 * 10 ** 16, 'ETH')
        for address in half_paid_addresses:
            self.purchase(address, 1 * 10 ** 16, 'ETH')

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

    def test_send_requested_currency(self):
        """Test for send_requested_currency"""
        users = db.get_users()
        successful_address = [
            db.get_payment_address(users['callsign_0']['pubkey'], 500, 'ETH', 'XLM'),
            db.get_payment_address(users['callsign_1']['pubkey'], 500, 'ETH', 'XLM'),
            db.get_payment_address(users['callsign_2']['pubkey'], 500, 'ETH', 'BUL')
        ]
        failed_address = [
            db.get_payment_address(users['callsign_3']['pubkey'], 500, 'ETH', 'BUL'),
            db.get_payment_address(users['callsign_4']['pubkey'], 500, 'ETH', 'BUL'),
            db.get_payment_address(users['callsign_5']['pubkey'], 500, 'ETH', 'BUL')
        ]
        routines.create_new_account(users['callsign_5']['pubkey'], 50000000)
        self.set_trust(users['callsign_5']['pubkey'], self.actual_keypairs[users['callsign_5']['pubkey']], 1000000)
        self.set_trust(users['callsign_2']['pubkey'], self.actual_keypairs[users['callsign_2']['pubkey']])
        for address in successful_address + failed_address:
            self.purchase(address, 15 * 10 ** 16, 'ETH')

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



class BalanceTest(unittest.TestCase):
    """Test getting balance for ETH/BTC addresses"""

    def test_btc_address(self):
        """Test balance with valid BTC address"""
        routines.get_btc_balance('2N6WqqshyxoWuBGHLjbwnWAQSigJ4TJkYrt')

    def test_invalid_btc_address(self):
        """Test balance with invalid BTC address"""
        with self.assertRaises(routines.BalanceError):
            routines.get_btc_balance('invalid_address')

    def test_eth_address(self):
        """Test balance with valid ETH address"""
        routines.get_eth_balance('0xce85247b032f7528ba97396f7b17c76d5d034d2f')

    def test_invalid_eth_address(self):
        """Test balance with invalid ETH address"""
        with self.assertRaises(routines.BalanceError):
            routines.get_eth_balance('invalid_address')
