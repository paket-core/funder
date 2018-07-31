"""PaKeT database interface."""
import logging
import os
import time

import pywallet.wallet

import util.db

import csl_reader

LOGGER = logging.getLogger('pkt.funder.db')
DEBUG = bool(os.environ.get('PAKET_DEBUG'))
XPUB = os.environ.get('PAKET_PAYMENT_XPUB')
DB_HOST = os.environ.get('PAKET_DB_HOST', '127.0.0.1')
DB_PORT = int(os.environ.get('PAKET_DB_PORT', 3306))
DB_USER = os.environ.get('PAKET_DB_USER', 'root')
DB_PASSWORD = os.environ.get('PAKET_DB_PASSWORD')
DB_NAME = os.environ.get('PAKET_DB_NAME', 'paket')
SQL_CONNECTION = util.db.custom_sql_connection(DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME)
MINIMUM_PAYMENT = int(os.environ.get('PAKET_MINIMUM_PAYMENT', 500))
BASIC_MONTHLY_ALLOWANCE = int(os.environ.get('PAKET_BASIC_MONTHLY_ALLOWANCE', 5000))


class UnknownUser(Exception):
    """Requested user does not exist."""


def init_db():
    """Initialize the database."""
    with SQL_CONNECTION() as sql:
        sql.execute('''
            CREATE TABLE users(
                pubkey VARCHAR(56) PRIMARY KEY,
                call_sign VARCHAR(32) UNIQUE NOT NULL)''')
        LOGGER.debug('users table created')
        sql.execute('''
            CREATE TABLE internal_user_infos(
                timestamp TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                pubkey VARCHAR(56),
                full_name VARCHAR(256),
                phone_number VARCHAR(32),
                address VARCHAR(1024),
                PRIMARY KEY (timestamp, pubkey),
                FOREIGN KEY(pubkey) REFERENCES users(pubkey))''')
        LOGGER.debug('internal_user_infos table created')
        sql.execute('''
            CREATE TABLE test_results(
                timestamp TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                pubkey VARCHAR(56) NOT NULL,
                name VARCHAR(64) NOT NULL,
                result INTEGER,
                PRIMARY KEY (timestamp, pubkey),
                FOREIGN KEY(pubkey) REFERENCES users(pubkey))''')
        LOGGER.debug('test_results table created')
        sql.execute('''
            CREATE TABLE purchases(
                timestamp TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                user_pubkey VARCHAR(56) NOT NULL,
                payment_pubkey VARCHAR(56) NOT NULL,
                payment_currency VARCHAR(3) NOT NULL,
                requested_currency VARCHAR(3) NOT NULL DEFAULT 'BUL',
                euro_cents INTEGER NOT NULL,
                paid INTEGER DEFAULT 0,
                FOREIGN KEY(user_pubkey) REFERENCES users(pubkey))''')
        LOGGER.debug('purchases table created')


def create_user(pubkey, call_sign):
    """Create a new user."""
    with SQL_CONNECTION() as sql:
        sql.execute("INSERT INTO users (pubkey, call_sign) VALUES (%s, %s)", (pubkey, call_sign))


def get_user(pubkey=None, call_sign=None):
    """Get user pubkey, call_sign, and purchase allowance from either pubkey or call_sign."""
    assert bool(pubkey or call_sign) != bool(pubkey and call_sign), 'specify either pubkey or call_sign'
    condition = ('pubkey', pubkey) if pubkey else ('call_sign', call_sign)
    with SQL_CONNECTION() as sql:
        sql.execute("SELECT * FROM users WHERE {} = %s LIMIT 1".format(condition[0]), (condition[1], ))
        try:
            return sql.fetchall()[0]
        except IndexError:
            raise UnknownUser("user with {} {} does not exists".format(*condition))


def update_test(pubkey, test_name, result=None):
    """Update a test for a user."""
    with SQL_CONNECTION() as sql:
        try:
            sql.execute("INSERT INTO test_results (pubkey, name, result) VALUES (%s, %s, %s)", (
                pubkey, test_name, result))
        except util.db.mysql.connector.IntegrityError:
            raise UnknownUser("no user with pubkey {}".format(pubkey))


def get_test_result(pubkey, test_name):
    """Get the latest result of a test."""
    with SQL_CONNECTION() as sql:
        sql.execute("SELECT result FROM test_results WHERE pubkey = %s AND name = %s ORDER BY timestamp DESC LIMIT 1", (
            pubkey, test_name))
        try:
            return sql.fetchall()[0]['result']
        except IndexError:
            return 0


def get_user_infos(pubkey):
    """Get all user infos."""
    with SQL_CONNECTION() as sql:
        sql.execute(
            "SELECT * FROM internal_user_infos WHERE pubkey = %s ORDER BY timestamp DESC LIMIT 1", (pubkey,))
        try:
            return {
                key.decode('utf8') if isinstance(key, bytes) else key: val
                for key, val in sql.fetchall()[0].items()}
        except IndexError:
            return {}


def set_internal_user_info(pubkey, **kwargs):
    """Add optional details in local user info."""
    # Verify user exists.
    get_user(pubkey)

    user_details = get_user_infos(pubkey)
    if kwargs:
        user_details.update(kwargs)
        user_details['pubkey'] = pubkey
        if 'timestamp' in user_details:
            del user_details['timestamp']
        with SQL_CONNECTION() as sql:
            sql.execute("INSERT INTO internal_user_infos ({}) VALUES ({})".format(
                ', '.join(user_details.keys()), ', '.join(['%s' for key in user_details])
            ), (list(user_details.values())))

        # Run basic test as soon as (and every time) all basic details are filled.
        if all([user_details.get(key) for key in ['full_name', 'phone_number', 'address']]):
            update_test(pubkey, 'basic', csl_reader.CSLListChecker().basic_test(user_details['full_name']))

    return user_details


def get_monthly_allowance(pubkey):
    """Get a user's monthly allowance."""
    return BASIC_MONTHLY_ALLOWANCE if get_test_result(pubkey, 'basic') > 0 else 0


def get_monthly_expanses(pubkey):
    """Get a user's expanses in the last month."""
    with SQL_CONNECTION() as sql:
        sql.execute("""
            SELECT CAST(SUM(euro_cents) AS SIGNED) euro_cents FROM purchases
            WHERE user_pubkey = %s AND timestamp > %s AND paid > 0""", (
                pubkey, time.time() - (30 * 24 * 60 * 60)))
        try:
            return sql.fetchall()[0][b'euro_cents'] or 0
        except TypeError:
            return 0


def get_payment_address(user_pubkey, euro_cents, payment_currency, requested_currency):
    """Get an address to pay for a purchase."""
    assert payment_currency in ['BTC', 'ETH'], 'payment_currency must be BTC or ETH'
    assert requested_currency in ['BUL', 'XLM'], 'requested_currency must be BUL or XLM'
    remaining_monthly_allowance = get_monthly_allowance(user_pubkey) - get_monthly_expanses(user_pubkey)
    assert remaining_monthly_allowance >= int(euro_cents), \
        "{} is allowed to purchase up to {} euro-cents when {} are required".format(
            user_pubkey, remaining_monthly_allowance, euro_cents)

    network = "btc{}".format('test' if DEBUG else '') if payment_currency.upper() == 'BTC' else 'ethereum'
    payment_pubkey = pywallet.wallet.create_address(network=network, xpub=XPUB)['address']
    with SQL_CONNECTION() as sql:
        sql.execute(
            """INSERT INTO purchases (user_pubkey, payment_pubkey, payment_currency, euro_cents, requested_currency)
            VALUES (%s, %s, %s, %s, %s)""",
            (user_pubkey, payment_pubkey, payment_currency, euro_cents, requested_currency))
    return payment_pubkey


def get_purchases():
    """Get all purchases"""
    with SQL_CONNECTION() as sql:
        sql.execute('SELECT * FROM purchases')
        return sql.fetchall()


def get_unpaid():
    """Get all unpaid addresses."""
    with SQL_CONNECTION() as sql:
        sql.execute('SELECT * FROM purchases WHERE paid = 0')
        return sql.fetchall()


def get_paid():
    """Get all paid addresses."""
    with SQL_CONNECTION() as sql:
        sql.execute('SELECT * FROM purchases WHERE paid = 1')
        return sql.fetchall()


def update_purchase(payment_pubkey, paid_status):
    """Update purchase status"""
    with SQL_CONNECTION() as sql:
        sql.execute("UPDATE purchases SET paid = %s WHERE payment_pubkey = %s", (paid_status, payment_pubkey))


def get_users():
    """Get list of users and their details - for debug only."""
    with SQL_CONNECTION() as sql:
        sql.execute('SELECT * FROM users')
        return {user['call_sign']: dict(
            get_user_infos(user['pubkey']),
            monthly_allowance=get_monthly_allowance(user['pubkey']),
            monthly_expanses=get_monthly_expanses(user['pubkey'])
        ) for user in sql.fetchall()}
