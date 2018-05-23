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
                paket_user VARCHAR(32) UNIQUE NOT NULL)''')
        LOGGER.debug('users table created')
        sql.execute('''
            CREATE TABLE credential_types(
                id INTEGER PRIMARY KEY,
                description VARCHAR(1024) NOT NULL)''')
        LOGGER.debug('credential_types table created')
        sql.execute('''
            INSERT INTO credential_types(id, description) VALUES
                (1, 'internal'),
                (2, 'civic')''')
        LOGGER.debug('credential_types table populated')
        sql.execute('''
            CREATE TABLE internal_credentials(
                id INTEGER PRIMARY KEY,
                full_name VARCHAR(256),
                phone_number VARCHAR(32),
                address VARCHAR(1024))''')
        LOGGER.debug('internal_credentials table populated')
        sql.execute('''
            CREATE TABLE user_credentials(
                pubkey VARCHAR(42) NOT NULL,
                credential_type INTEGER NOT NULL,
                credential_id NOT NULL,
                FOREIGN KEY(pubkey) REFERENCES users(pubkey),
                FOREIGN KEY(credential_type) REFERENCES credential_types(id))''')
        LOGGER.debug('user_credentials table created')
        sql.execute('''
            CREATE TABLE test_results(
                pubkey VARCHAR(42) NOT NULL,
                test_name VARCHAR(64) NOT NULL,
                result INTEGER,
                FOREIGN KEY(pubkey) REFERENCES users(pubkey))''')
        LOGGER.debug('test_results table created')


def create_user(pubkey, paket_user):
    """Create a new user."""
    with sql_connection() as sql:
        try:
            sql.execute("INSERT INTO users (pubkey, paket_user) VALUES (?, ?)", (pubkey, paket_user))
        except sqlite3.IntegrityError as exception:
            bad_column_name = str(exception).split('.')[-1]
            bad_value = locals().get(bad_column_name)
            raise AssertionError("{} {} is non unique".format(bad_column_name, bad_value))


def get_user(pubkey=None, paket_user=None):
    """Get user pubkey, paket_user, and purchase allowance from either pubkey or paket_user."""
    assert bool(pubkey or paket_user) != bool(pubkey and paket_user), 'specify either pubkey or paket_user'
    condition = ('pubkey', pubkey) if pubkey else ('paket_user', paket_user)
    with sql_connection() as sql:
        sql.execute("SELECT * FROM users WHERE {} = ?".format(condition[0]), (condition[1],))
        try:
            return dict(sql.fetchone(), purchase_allowance='50$ a month')
        except TypeError:
            raise AssertionError("user with {} {} does not exists".format(*condition))


#def create_credential(pubkey)
#
#
#def update_user_details(pubkey, **kwargs):
#    """Create a new user."""
#    with sql_connection() as sql:
#        sql.execute('SELECT * FROM users LIMIT 1')
#        columns = [column[0] for column in sql.description]
#        nonexisting_columns = set(kwargs.keys()) - set(columns)
#        if nonexisting_columns:
#            raise AssertionError("users do not support the following fields: {}".format(nonexisting_columns))
#        for key, value in kwargs.items():
#            sql.execute("UPDATE users SET {} = ? WHERE pubkey = ?".format(key), (value, pubkey))
#
#
#def get_user(pubkey):
#    """Get user details."""
#    with sql_connection() as sql:
#        sql.execute("SELECT * FROM users WHERE users.pubkey = ?", (pubkey,))
#        user = sql.fetchone()
#        assert user is not None, "Unknown user with pubkey {}".format(pubkey)
#        return {key: user[key] for key in user.keys()} if user else None


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




#def create_user(pubkey, paket_user, seed=None):
#    """Create a new user."""
#    with sql_connection() as sql:
#        try:
#            sql.execute("INSERT INTO users (pubkey, paket_user) VALUES (?, ?)", (pubkey, paket_user))
#            if seed is not None:
#                sql.execute("INSERT INTO keys (pubkey, seed) VALUES (?, ?)", (pubkey, seed))
#        except sqlite3.IntegrityError as exception:
#            bad_column_name = str(exception).split('.')[-1]
#            bad_value = locals().get(bad_column_name)
#            raise DuplicateUser("{} {} is non unique".format(bad_column_name, bad_value))
#
#
#def get_user(pubkey):
#    """Get user details."""
#    with sql_connection() as sql:
#        sql.execute("""
#            SELECT * FROM users
#            LEFT JOIN keys on users.pubkey = keys.pubkey
#            WHERE users.pubkey = ?""", (pubkey,))
#        user = sql.fetchone()
#        if user is None:
#            raise UnknownUser("Unknown user with pubkey {}".format(pubkey))
#        return {key: user[key] for key in user.keys()} if user else None
#
#
#def update_user_details(pubkey, full_name, phone_number):
#    """Update user details."""
#    with sql_connection() as sql:
#        sql.execute("""
#            UPDATE users SET
#            full_name = ?,
#            phone_number = ?
#            WHERE pubkey = ?""", (full_name, phone_number, pubkey))
#    return get_user(pubkey)
#
#
#def get_users():
#    """Get list of users and their details - for debug only."""
#    with sql_connection() as sql:
#        sql.execute('SELECT * FROM users')
#        users = sql.fetchall()
#    return {user['pubkey']: {key: user[key] for key in user.keys() if key != 'pubkey'} for user in users}
#
#
#
#
#
#
#
## Sandbox setup.
#
#
#def create_db_user(paket_user, pubkey):
#    """Create a new user in the DB."""
#    LOGGER.debug("Creating user %s", paket_user)
#    try:
#        db.create_user(pubkey, paket_user)
#        db.update_user_details(pubkey, paket_user, '123-456')
#        webserver.validation.update_nonce(pubkey, 1, paket_user)
#    except db.DuplicateUser:
#        LOGGER.debug("User %s already exists", paket_user)
#
#
#def init_sandbox():
#    """Initialize database with debug values and fund users. For debug only."""
#    webserver.validation.init_nonce_db()
#    db.init_db()
#    for paket_user, pubkey in [
#            (key.split('PAKET_USER_', 1)[1], value)
#            for key, value in os.environ.items()
#            if key.startswith('PAKET_USER_')
#    ]:
#        create_db_user(paket_user, pubkey)
