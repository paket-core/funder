"""Tests for routines module"""
import unittest

import db
import routines


class RoutinesTest(unittest.TestCase):
    """Test for routines"""

    @classmethod
    def setUpClass(cls):
        """Create tables if they does not exists"""
        try:
            db.init_db()
        except:
            pass

    def setUp(self):
        """Insert data into tables"""
        db.util.db.clear_tables(db.SQL_CONNECTION, db.DB_NAME)
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
                """INSERT INTO purchases (user_pubkey, payment_pubkey,
                payment_currency, requested_currency, euro_cents, paid)
                VALUES ('GAPAVB6IW4UNQTP4XFSRF4L6PS2XZD22IG6Z6FV6FXGZV7T3VL4TOAYQ',
                '2N6WqqshyxoWuBGHLjbwnWAQSigJ4TJkYrt', 'BTC', 'BUL', '600', '1')""")
            sql.execute(
                """INSERT INTO purchases (user_pubkey, payment_pubkey,
                payment_currency, requested_currency, euro_cents, paid)
                VALUES ('GAPAVB6IW4UNQTP4XFSRF4L6PS2XZD22IG6Z6FV6FXGZV7T3VL4TOAYQ',
                '0xBAEc12c49fea1f3AC84Fa9DC2A8A3559Fe81bC5F', 'ETH', 'BUL', '500', '0')""")
            sql.execute(
                """INSERT INTO purchases (user_pubkey, payment_pubkey,
                payment_currency, requested_currency, euro_cents, paid)
                VALUES ('GBD5666CDBM6MS3RKXLO5WOXVJXECOCLBAE6B62XMNKZLF63GC6V3IB5',
                '0x2F41CCaD2466AdFe3A5C1Ed60b1589e125130ef3', 'ETH', 'BUL', '100', '0')""")
            sql.execute(
                """INSERT INTO purchases (user_pubkey, payment_pubkey,
                payment_currency, requested_currency, euro_cents, paid)
                VALUES ('GDZYRJQTZ7LG2MIJJ35MTY55D7MTM7RV533KNBGXSU47Q5DMGLDXONBR',
                '0x3dcf887038BC4BD4710fEe6B49ecE233482B377F', 'ETH', 'BUL', '1200', '0')""")
            sql.execute(
                """INSERT INTO purchases (user_pubkey, payment_pubkey,
                payment_currency, requested_currency, euro_cents, paid)
                VALUES ('GDZYRJQTZ7LG2MIJJ35MTY55D7MTM7RV533KNBGXSU47Q5DMGLDXONBR',
                '2NBMEXediyAYCGcVfW5W2toR5Kui1EpqaYB', 'BTC', 'XLM', '800', '0')""")


    def test_check_purchases_addresses(self):
        """Test for check_purchases_addresses routine"""
        routines.check_purchases_addresses()
        # TODO: add checks for result

    def test_send_requested_currency(self):
        """Test for send_requested_currency"""
        routines.send_requested_currency()
        # TODO: add checks for result


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
