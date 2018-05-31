"""PaKeT database interface."""
import logging
import sqlite3
import time

import pywallet.wallet

import util.db

LOGGER = logging.getLogger('pkt.funder.db')
DB_NAME = 'funder.db'
SEED = ('client ancient calm uncover opinion coil priority misery empty favorite moment myth')
XPUB = 'xpub69Jm1CxJ8kdGZuqy3mkoKekzN1h4KNKUJiTsUQ9Hc1do6Rs5BEEFi2VYJJGSWVpURv4Nq3g4C3JTsxPUzEk9EVcTGuE2VuyhW7KpmsDe4bJ'


class UserNotFound(Exception):
    """Requested user does not exist."""


def get_table_columns(table_name):
    """Get the fields of a specific table."""
    with util.db.sql_connection(DB_NAME) as sql:
        sql.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?", (table_name,))
        assert sql.fetchone(), "table {} does not exist".format(table_name)
        sql.execute("SELECT * FROM {} LIMIT 1".format(table_name))
        return [column[0] for column in sql.description]


def verify_columns(table_name, accessed_columns):
    """Raise an exception if table_name does not contain all of accessed_columns."""
    nonexisting_columns = set(accessed_columns) - set(get_table_columns(table_name))
    if nonexisting_columns:
        raise AssertionError("users do not support the following fields: {}".format(nonexisting_columns))


def init_db():
    """Initialize the database."""
    with util.db.sql_connection(DB_NAME) as sql:
        # Not using IF EXISTS here in case we want different handling.
        sql.execute('SELECT name FROM sqlite_master WHERE type = "table" AND name = "users"')
        if len(sql.fetchall()) == 1:
            LOGGER.debug('database already exists')
            return
        sql.execute('''
            CREATE TABLE users(
                pubkey VARCHAR(42) PRIMARY KEY,
                call_sign VARCHAR(32) UNIQUE NOT NULL)''')
        LOGGER.debug('users table created')
        sql.execute('''
            CREATE TABLE internal_user_infos(
                pubkey VARCHAR(42) PRIMARY KEY,
                full_name VARCHAR(256),
                phone_number VARCHAR(32),
                address VARCHAR(1024),
                FOREIGN KEY(pubkey) REFERENCES users(pubkey))''')
        LOGGER.debug('internal_user_infos table populated')
        sql.execute('''
            CREATE TABLE test_results(
                pubkey VARCHAR(42) NOT NULL,
                name VARCHAR(64) NOT NULL,
                result INTEGER,
                FOREIGN KEY(pubkey) REFERENCES users(pubkey))''')
        LOGGER.debug('test_results table created')
        sql.execute('''
            CREATE TABLE purchases(
                timestamp INTEGER NOT NULL DEFAULT CURRENT_TIMESTAMP,
                user_pubkey VARCHAR(42) NOT NULL,
                payment_pubkey VARCHAR(42) NOT NULL,
                payment_currency VARCHAR(3) NOT NULL,
                euro_cents INTEGER NOT NULL,
                paid INTEGER DEFAULT 0,
                FOREIGN KEY(user_pubkey) REFERENCES users(pubkey))''')
        LOGGER.debug('purchases table created')


def create_user(pubkey, call_sign):
    """Create a new user."""
    with util.db.sql_connection(DB_NAME) as sql:
        try:
            sql.execute("INSERT INTO users (pubkey, call_sign) VALUES (?, ?)", (pubkey, call_sign))
        except sqlite3.IntegrityError as exception:
            bad_column_name = str(exception).split('.')[-1]
            bad_value = locals().get(bad_column_name)
            raise AssertionError("{} {} is non unique".format(bad_column_name, bad_value))


def get_user(pubkey=None, call_sign=None):
    """Get user pubkey, call_sign, and purchase allowance from either pubkey or call_sign."""
    assert bool(pubkey or call_sign) != bool(pubkey and call_sign), 'specify either pubkey or call_sign'
    condition = ('pubkey', pubkey) if pubkey else ('call_sign', call_sign)
    with util.db.sql_connection(DB_NAME) as sql:
        sql.execute("SELECT * FROM users WHERE {} = ?".format(condition[0]), (condition[1],))
        try:
            return dict(sql.fetchone())
        except TypeError:
            raise UserNotFound("user with {} {} does not exists".format(*condition))


def update_test(pubkey, test_name, result=None):
    """Update a test for a user."""
    with util.db.sql_connection(DB_NAME) as sql:
        try:
            sql.execute("INSERT INTO test_results (pubkey, name, result) VALUES (?, ?, ?)", (
                pubkey, test_name, result))
        except sqlite3.IntegrityError:
            raise UserNotFound("no user with pubkey {}".format(pubkey))


def get_test_result(pubkey, test_name):
    """Get the latest result of a test."""
    with util.db.sql_connection(DB_NAME) as sql:
        sql.execute("SELECT result FROM test_results WHERE pubkey = ? AND name = ? GROUP BY pubkey", (
            pubkey, test_name))
        try:
            return sql.fetchone()['result']
        except TypeError:
            return 0


def set_internal_user_info(pubkey, **kwargs):
    """Add or update optional details in local user info."""
    verify_columns('internal_user_infos', kwargs.keys())
    with util.db.sql_connection(DB_NAME) as sql:
        try:
            sql.execute("INSERT INTO internal_user_infos (pubkey) VALUES (?)", (pubkey,))
        except sqlite3.IntegrityError:
            pass
        try:
            for key, value in kwargs.items():
                sql.execute("UPDATE internal_user_infos SET {} = ? WHERE pubkey = ?".format(key), (value, pubkey))
        except sqlite3.IntegrityError:
            raise AssertionError("{} = {} is not a valid user detail".format(key, value))
    if 'address' in kwargs:
        update_test(pubkey, 'basic', 1)


def get_user_infos(pubkey):
    """Get all user infos."""
    with util.db.sql_connection(DB_NAME) as sql:
        sql.execute("""
            SELECT * FROM users
            LEFT JOIN internal_user_infos on users.pubkey = internal_user_infos.pubkey
            WHERE users.pubkey = ?""", (pubkey,))
        try:
            return dict(sql.fetchone())
        except TypeError:
            raise UserNotFound("user with pubkey {} does not exists".format(pubkey))


def get_monthly_allowance(pubkey):
    """Get a user's monthly allowance."""
    return 500 if get_test_result(pubkey, 'basic') > 0 else 0


def get_monthly_expanses(pubkey):
    """Get a user's expanses in the last month."""
    with util.db.sql_connection(DB_NAME) as sql:
        sql.execute("""
            SELECT SUM(euro_cents) FROM purchases
            WHERE user_pubkey = ? AND timestamp > ? AND paid = 1""", (pubkey, time.time() - (30 * 24 * 60 * 60)))
        try:
            return sql.fetchone()[0] or 0
        except TypeError:
            return 0


def get_users():
    """Get list of users and their details - for debug only."""
    with util.db.sql_connection(DB_NAME) as sql:
        sql.execute('''
            SELECT * FROM users
            LEFT JOIN internal_user_infos on users.pubkey = internal_user_infos.pubkey
            LEFT JOIN test_results on users.pubkey = test_results.pubkey''')
        return {user['pubkey']: dict(
            user,
            monthly_allowance=get_monthly_allowance(user['pubkey']),
            monthly_expanses=get_monthly_expanses(user['pubkey'])
        ) for user in sql.fetchall()}


def get_payment_address(user_pubkey, euro_cents, payment_currency):
    """Get an address to pay for a purchase."""
    assert payment_currency in ['BTC', 'ETH'], 'payment_currency must be BTC or ETH'
    remaining_monthly_allowance = get_monthly_allowance(user_pubkey) - get_monthly_expanses(user_pubkey)
    assert remaining_monthly_allowance >= euro_cents, \
        "{} is allowed to purchase up to {} euro-cents when {} are required".format(
            user_pubkey, remaining_monthly_allowance, euro_cents)

    payment_pubkey = pywallet.wallet.create_address(network=payment_currency, xpub=XPUB)['address']
    with util.db.sql_connection(DB_NAME) as sql:
        sql.execute(
            "INSERT INTO purchases (user_pubkey, payment_pubkey, payment_currency, euro_cents) VALUES (?, ?, ?, ?)",
            (user_pubkey, payment_pubkey, payment_currency, euro_cents))
    return payment_pubkey
