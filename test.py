"""Test Funder."""
import unittest

import util.logger

import db
import routines

LOGGER = util.logger.logging.getLogger('pkt.funder.test')
util.logger.setup()


class DBTest(unittest.TestCase):
    """Testing the database module."""

    def setUp(self):
        assert db.DB_NAME.startswith('test'), "refusing to test on db named {}".format(db.DB_NAME)
        LOGGER.info('clearing database')
        db.clear_tables()

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


class RoutinesTest(unittest.TestCase):
    """Test for routines"""

    @classmethod
    def setUpClass(cls):
        """Initialize db with tables and clear them if they exist."""
        db.init_db()
        db.clear_tables()

    @classmethod
    def tearDownClass(cls):
        """Clear tables"""
        db.clear_tables()

    def setUp(self):
        """Insert data into tables"""
        db.create_user('GAPAVB6IW4UNQTP4XFSRF4L6PS2XZD22IG6Z6FV6FXGZV7T3VL4TOAYQ', 'callsign1')
        db.create_user('GBLZA2SZ3XJLCFYKW7TF6Q7FAMA4WJUOZN6J6WM3Z676W3JOJDQ6CEKE', 'callsign2')
        db.create_user('GBD5666CDBM6MS3RKXLO5WOXVJXECOCLBAE6B62XMNKZLF63GC6V3IB5', 'callsign3')
        db.create_user('GC2QTLYQXYFEOFQ26QNEDZR5VQVHLQPCXA5S4JU64OMW5IXFF5J4L52Z', 'callsign4')
        db.create_user('GDZYRJQTZ7LG2MIJJ35MTY55D7MTM7RV533KNBGXSU47Q5DMGLDXONBR', 'callsign5')
        with db.SQL_CONNECTION() as sql:
            sql.execute(
                """INSERT INTO test_results (pubkey, name, result)
                VALUES ('GAPAVB6IW4UNQTP4XFSRF4L6PS2XZD22IG6Z6FV6FXGZV7T3VL4TOAYQ', 'basic', '1')""")
            sql.execute(
                """INSERT INTO test_results (pubkey, name, result)
                VALUES ('GBLZA2SZ3XJLCFYKW7TF6Q7FAMA4WJUOZN6J6WM3Z676W3JOJDQ6CEKE', 'basic', '0')""")
            sql.execute(
                """INSERT INTO test_results (pubkey, name, result)
                VALUES ('GBD5666CDBM6MS3RKXLO5WOXVJXECOCLBAE6B62XMNKZLF63GC6V3IB5', 'basic', '1')""")
            sql.execute(
                """INSERT INTO test_results (pubkey, name, result)
                VALUES ('GC2QTLYQXYFEOFQ26QNEDZR5VQVHLQPCXA5S4JU64OMW5IXFF5J4L52Z', 'basic', '0')""")
            sql.execute(
                """INSERT INTO test_results (pubkey, name, result)
                VALUES ('GDZYRJQTZ7LG2MIJJ35MTY55D7MTM7RV533KNBGXSU47Q5DMGLDXONBR', 'basic', '1')""")
        # TODO: change these addresses for 'inactive'
        with db.SQL_CONNECTION() as sql:
            sql.execute(
                """INSERT INTO purchases (timestamp, user_pubkey, payment_pubkey,
                payment_currency, requested_currency, euro_cents, paid)
                VALUES ('1529508977', 'GAPAVB6IW4UNQTP4XFSRF4L6PS2XZD22IG6Z6FV6FXGZV7T3VL4TOAYQ',
                '1B8ipdHMD9bTucyhpYCEicMXBNP6MJKMMS', 'BTC', 'BUL', '600', '1')""")
            sql.execute(
                """INSERT INTO purchases (timestamp, user_pubkey, payment_pubkey,
                payment_currency, requested_currency, euro_cents, paid)
                VALUES ('1529572364', 'GAPAVB6IW4UNQTP4XFSRF4L6PS2XZD22IG6Z6FV6FXGZV7T3VL4TOAYQ',
                '0x8AD9062288A4081BDBDB488DA0099B4E1D87DDF8', 'ETH', 'BUL', '500', '0')""")
            sql.execute(
                """INSERT INTO purchases (timestamp, user_pubkey, payment_pubkey,
                payment_currency, requested_currency, euro_cents, paid)
                VALUES ('1529043322', 'GBD5666CDBM6MS3RKXLO5WOXVJXECOCLBAE6B62XMNKZLF63GC6V3IB5',
                '0x8b9bb1e80a765553052e358452091cbe0ab9d114', 'ETH', 'BUL', '100', '0')""")
            sql.execute(
                """INSERT INTO purchases (timestamp, user_pubkey, payment_pubkey,
                payment_currency, requested_currency, euro_cents, paid)
                VALUES ('1529679314', 'GDZYRJQTZ7LG2MIJJ35MTY55D7MTM7RV533KNBGXSU47Q5DMGLDXONBR',
                '0x580ce178db05e6826f9fdef8c8645e32b9865f0a', 'ETH', 'BUL', '1200', '0')""")
            sql.execute(
                """INSERT INTO purchases (timestamp, user_pubkey, payment_pubkey,
                payment_currency, requested_currency, euro_cents, paid)
                VALUES ('1529693109', 'GDZYRJQTZ7LG2MIJJ35MTY55D7MTM7RV533KNBGXSU47Q5DMGLDXONBR',
                '17kHGHDgE7q2JDkZjbDHagkKMreyo9XwRS', 'BTC', 'XLM', '800', '0')""")

    def tearDown(self):
        """Clear tables"""
        db.clear_tables()

    def test_check_purchases_addresses(self):
        """Test for check_purchases_addresses routine"""
        routines.check_purchases_addresses()
        # TODO: add checks for result

    def send_requested_currency(self):
        """Test for send_requested_currency"""
        routines.send_requested_currency()
        # TODO: add checks for result


class BalanceTest(unittest.TestCase):
    """Test getting balance for ETH/BTC addresses"""

    def test_btc_address(self):
        """Test balance with valid BTC address"""
        routines.get_btc_balance('17kHGHDgE7q2JDkZjbDHagkKMreyo9XwRS')

    def test_invalid_btc_address(self):
        """Test balance with invalid BTC address"""
        with self.assertRaises(routines.BalanceError):
            routines.get_btc_balance('invalid_address')

    def test_eth_address(self):
        """Test balance with valid ETH address"""
        routines.get_eth_balance('17kHGHDgE7q2JDkZjbDHagkKMreyo9XwRS')

    def test_invalid_eth_address(self):
        """Test balance with invalid ETH address"""
        routines.get_eth_balance('invalid_address')


if __name__ == '__main__':
    unittest.main()
