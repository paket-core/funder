"""PaKeT database interface."""
import contextlib
import logging
import sqlite3

LOGGER = logging.getLogger('pkt.funder.db')
DB_NAME = 'funder.db'


@contextlib.contextmanager
def sql_connection(db_name=None):
    """Context manager for querying the database."""
    try:
        connection = sqlite3.connect(db_name or DB_NAME)
        connection.row_factory = sqlite3.Row
        yield connection.cursor()
        connection.commit()
    except sqlite3.Error as db_exception:
        raise db_exception
    finally:
        if 'connection' in locals():
            # noinspection PyUnboundLocalVariable
            connection.close()


def get_table_columns(table_name):
    """Get the fields of a specific table."""
    with sql_connection() as sql:
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
    with sql_connection() as sql:
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
                test_name VARCHAR(64) NOT NULL,
                result INTEGER,
                FOREIGN KEY(pubkey) REFERENCES users(pubkey))''')
        LOGGER.debug('test_results table created')


def create_user(pubkey, call_sign):
    """Create a new user."""
    with sql_connection() as sql:
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
    with sql_connection() as sql:
        sql.execute("SELECT * FROM users WHERE {} = ?".format(condition[0]), (condition[1],))
        try:
            return dict(sql.fetchone(), purchase_allowance='50$ a month')
        except TypeError:
            raise AssertionError("user with {} {} does not exists".format(*condition))


def set_internal_user_info(pubkey, **kwargs):
    """Add or update optional details in local user info."""
    verify_columns('internal_user_infos', kwargs.keys())
    with sql_connection() as sql:
        try:
            sql.execute("INSERT INTO internal_user_infos (pubkey) VALUES (?)", (pubkey,))
        except sqlite3.IntegrityError:
            pass
        for key, value in kwargs.items():
            sql.execute("UPDATE internal_user_infos SET {} = ? WHERE pubkey = ?".format(key), (value, pubkey))


def get_user_infos(pubkey):
    """Get all user infos."""
    with sql_connection() as sql:
        sql.execute("""
            SELECT * FROM users
            LEFT JOIN internal_user_infos on users.pubkey = internal_user_infos.pubkey
            WHERE users.pubkey = ?""", (pubkey,))
        return dict(sql.fetchone())


def get_users():
    """Get list of users and their details - for debug only."""
    with sql_connection() as sql:
        sql.execute('''
            SELECT * FROM users
            LEFT JOIN internal_user_infos on users.pubkey = internal_user_infos.pubkey''')
        return {user['pubkey']: dict(user) for user in sql.fetchall()}


def update_test(test_name, pubkey, result=None):
    """Update a test for a user."""
    with sql_connection() as sql:
        try:
            sql.execute("INSERT INTO test_results (test_name, pubkey, result) VALUES (?, ?, ?)", (
                test_name, pubkey, result))
        except sqlite3.IntegrityError:
            raise AssertionError("no user with pubkey {}".format(pubkey))


def get_test_result(test_name, pubkey):
    """Get the latest result of a test."""
    get_user(pubkey)
    with sql_connection() as sql:
        sql.execute("SELECT result FROM test_results WHERE test_name = ? AND pubkey = ? ORDER BY idx DESC LIMIT 1", (
            test_name, pubkey))
        try:
            return sql.fetchone()[0]
        except TypeError:
            return None
