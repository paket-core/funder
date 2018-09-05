"""PaKeT database interface."""
import logging
import os
import time

import pywallet.wallet
import authy.api

import paket_stellar
import util.db
import util.conversion

import csl_reader
import currency_conversions

AUTHY_API_KEY = os.environ.get('PAKET_AUTHY_API')
AUTHY_API = authy.api.AuthyApiClient(AUTHY_API_KEY)
LOGGER = logging.getLogger('pkt.funder.db')
DEBUG = bool(os.environ.get('PAKET_DEBUG'))
FUNDER_SEED = os.environ['PAKET_FUNDER_SEED']
XPUB = os.environ['PAKET_PAYMENT_XPUB']
DB_HOST = os.environ.get('PAKET_DB_HOST', '127.0.0.1')
DB_PORT = int(os.environ.get('PAKET_DB_PORT', 3306))
DB_USER = os.environ.get('PAKET_DB_USER', 'root')
DB_PASSWORD = os.environ.get('PAKET_DB_PASSWORD')
DB_NAME = os.environ.get('PAKET_DB_NAME', 'paket')
SQL_CONNECTION = util.db.custom_sql_connection(DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME)
# limits to fund (in euro-cents)
HOURLY_FUND_LIMIT = 5000
DAILY_FUND_LIMIT = 10000
XLM_STARTING_BALANCE = 1000000000 if DEBUG else 15000000 + currency_conversions.euro_cents_to_xlm_stroops(100)
BUL_STARTING_BALANCE = 1000000000 if DEBUG else currency_conversions.euro_cents_to_bul_stroops(500)
MINIMUM_PAYMENT = int(os.environ.get('PAKET_MINIMUM_PAYMENT', 500))
BASIC_MONTHLY_ALLOWANCE = int(os.environ.get('PAKET_BASIC_MONTHLY_ALLOWANCE', 5000))


class FundLimitReached(Exception):
    """Unable to fund account because fund limit was reached."""


class NotVerified(Exception):
    """User sent invalid or expired verification code."""


class PhoneAlreadyInUse(Exception):
    """Specified phone number already in use by another user."""


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
                authy_id varchar(56),
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
        sql.execute('''
            CREATE TABLE fundings(
                timestamp TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                user_pubkey VARCHAR(56) NOT NULL,
                currency VARCHAR(3),
                currency_amount INTEGER,
                euro_cents INTEGER,
                PRIMARY KEY (timestamp, user_pubkey),
                FOREIGN KEY(user_pubkey) REFERENCES users(pubkey))''')
        LOGGER.debug('fundings table created')


def send_verification_code(user_pubkey):
    """Send verification code to user's phone number."""
    user_info = set_internal_user_info(user_pubkey)

    if 'phone_number' not in user_info:
        # TODO : add custom exception
        raise AssertionError('phone number does not provided')

    if user_info['authy_id'] is not None:
        authy_id = user_info['authy_id']
    else:
        # FIXME: It is temporary workaround
        full_phone_number = user_info['phone_number'].replace('+', '')
        country_code = full_phone_number[:3]
        phone_number = full_phone_number[3:]
        authy_user = AUTHY_API.users.create('paket@mockemails.moc', phone_number, country_code)
        if not authy_user.ok():
            raise AssertionError(authy_user.errors())
        authy_id = authy_user.id
        set_internal_user_info(user_pubkey, authy_id=authy_id)

    # FIXME: Add proper error handling
    sms = AUTHY_API.users.request_sms(authy_id)
    if not sms.ok():
        raise AssertionError(sms.errors())


def check_verification_code(user_pubkey, verification_code):
    """
    Check verification code validity and create account
    if it was first phone verification.
    """
    authy_id = set_internal_user_info(user_pubkey).get('authy_id', None)
    if authy_id is None:
        # TODO: add some custom exception
        pass
    verification = AUTHY_API.tokens.verify(authy_id, verification_code)

    if not verification.ok():
        raise NotVerified('verification code invalid or expired')

    with SQL_CONNECTION() as sql:
        sql.execute("SELECT * FROM purchases WHERE user_pubkey = %s", (user_pubkey,))
        purchases = sql.fetchall()
    passed_kyc = get_test_result(user_pubkey, 'basic')
    if passed_kyc and not purchases:
        create_and_fund(user_pubkey)


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


def get_spent_euro(period):
    """Get spent euro-cents amount for specified period of time."""
    with SQL_CONNECTION() as sql:
        sql.execute('''
            SELECT CAST(SUM(euro_cents) AS SIGNED) euro_cents FROM fundings
            WHERE timestamp > %s''', (period,))
        try:
            return sql.fetchall()[0][b'euro_cents'] or 0
        except TypeError:
            return 0


def get_hourly_spent_euro():
    """Get spent euro-cents amount for last hour."""
    return get_spent_euro(3600)


def get_daily_spent_euro():
    """Get spent euro-cents amount for last 24 hours."""
    return get_spent_euro(86400)


def create_and_fund(user_pubkey):
    """Create account and fund it with starting XLM and BUL amounts"""
    daily_spent_euro = get_daily_spent_euro()
    if daily_spent_euro >= DAILY_FUND_LIMIT:
        raise FundLimitReached('daily fund limit reached')

    hourly_spent_euro = get_hourly_spent_euro()
    if hourly_spent_euro >= HOURLY_FUND_LIMIT:
        raise FundLimitReached('hourly fund limit reached')

    starting_balance = util.conversion.stroops_to_units(XLM_STARTING_BALANCE)
    funder_pubkey = paket_stellar.stellar_base.Keypair.from_seed(FUNDER_SEED).address().decode()
    builder = paket_stellar.gen_builder(funder_pubkey)
    builder.append_create_account_op(destination=user_pubkey, starting_balance=starting_balance)
    envelope = builder.gen_te().xdr().decode()
    paket_stellar.submit_transaction_envelope(envelope, seed=FUNDER_SEED)
    euro_cents = currency_conversions.currency_to_euro_cents('XLM', XLM_STARTING_BALANCE)
    with SQL_CONNECTION() as sql:
        sql.execute("""
            INSERT INTO fundings (user_pubkey, currency, currency_amount, euro_cents)
            VALUES (%s, %s, %s, %s)""", (user_pubkey, 'XLM', XLM_STARTING_BALANCE, euro_cents))


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
