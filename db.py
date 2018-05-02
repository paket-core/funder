"""PaKeT database interface."""
import contextlib
import logging
import sqlite3

LOGGER = logging.getLogger('pkt.identity.db')
DB_NAME = 'identity.db'


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
                full_name VARCHAR(256) NOT NULL,
                phone_number VARCHAR(32) NOT NULL,
                address VARCHAR(1024) NOT NULL,
                paket_user VARCHAR(32) UNIQUE NOT NULL)''')
        LOGGER.debug('users table created')
        sql.execute('''
            CREATE TABLE authorizations(
                authorized_pubkey VARCHAR(42) NOT NULL,
                viewd_pubkey VARCHAR(42) NOT NULL)''')
        LOGGER.debug('authorizations table created')


def create_user(pubkey, full_name, phone_number, address, paket_user):
    """Create a new user."""
    with sql_connection() as sql:
        try:
            sql.execute("""
                INSERT INTO users (pubkey, full_name, phone_number, address, paket_user)
                VALUES (?, ?, ?, ?, ?)""", (pubkey, full_name, phone_number, address, paket_user))
        except sqlite3.IntegrityError as exception:
            bad_column_name = str(exception).split('.')[-1]
            bad_value = locals().get(bad_column_name)
            raise AssertionError("{} {} is non unique".format(bad_column_name, bad_value))


def get_user(pubkey):
    """Get user details."""
    with sql_connection() as sql:
        sql.execute("SELECT * FROM users WHERE users.pubkey = ?", (pubkey,))
        user = sql.fetchone()
        assert user is not None, "Unknown user with pubkey {}".format(pubkey)
        return {key: user[key] for key in user.keys()} if user else None


def update_user_details(pubkey, full_name, phone_number, address):
    """Update user details."""
    with sql_connection() as sql:
        sql.execute("UPDATE users SET full_name = ?, phone_number = ?, address = ?  WHERE pubkey = ?", (
            full_name, phone_number, address, pubkey))
    return get_user(pubkey)


def is_authorized(authorized_pubkey, viewd_pubkey):
    """Check to see if authorized_pubkey is authorized to view viewd_pubkey."""
    with sql_connection() as sql:
        sql.execute("SELECT 1 FROM authorizations WHERE authorized_pubkey = ? AND viewd_pubkey = ?", (
            authorized_pubkey, viewd_pubkey))
        return sql.fetchone() is not None


def add_authorization(authorized_pubkey, viewd_pubkey):
    """Add authorization for authorized_pubkey to view details of viewd_pubkey."""
    if is_authorized(authorized_pubkey, viewd_pubkey):
        LOGGER.warning("pubkey %s is already authorized to view %s", authorized_pubkey, viewd_pubkey)
        return False
    with sql_connection() as sql:
        sql.execute("INSERT INTO authorizations (authorized_pubkey, viewd_pubkey) VALUES (?, ?)", (
            authorized_pubkey, viewd_pubkey))
    return True


def remove_authorization(authorized_pubkey, viewd_pubkey):
    """Remove authorization for authorized_pubkey to view details of viewd_pubkey."""
    if not is_authorized(authorized_pubkey, viewd_pubkey):
        LOGGER.warning("pubkey %s is already not authorized to view %s", authorized_pubkey, viewd_pubkey)
        return False
    with sql_connection() as sql:
        sql.execute("DELETE FROM authorizations WHERE authorized_pubkey = ? AND viewd_pubkey = ?", (
            authorized_pubkey, viewd_pubkey))
    return True
