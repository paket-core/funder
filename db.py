"""PAKET database interface."""
import logging
import os
import time

import pywallet.wallet
import authy.api
import phonenumbers

import paket_stellar
import util.db
import util.conversion

import csl_reader
import prices

VERIFY_API_KEY = os.environ.get('PAKET_VERIFY_API_KEY')
AUTHY_API = authy.api.AuthyApiClient(VERIFY_API_KEY)
VERIFY_CODE_LENGTH = int(os.environ.get('PAKET_VERIFY_CODE_LENGTH', 4))
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
HOURLY_FUND_LIMIT = int(os.environ.get('PAKET_HOURLY_FUND_LIMIT'))
DAILY_FUND_LIMIT = int(os.environ.get('PAKET_DAILY_FUND_LIMIT'))
EUR_XLM_STARTING_BALANCE = int(os.environ.get('PAKET_EUR_XLM_STARTING_BALANCE'))
EUR_BUL_STARTING_BALANCE = int(os.environ.get('PAKET_EUR_BUL_STARTING_BALANCE'))
XLM_STARTING_BALANCE = util.conversion.euro_cents_to_xlm_stroops(EUR_XLM_STARTING_BALANCE, prices.xlm_price())
BUL_STARTING_BALANCE = util.conversion.euro_cents_to_bul_stroops(EUR_BUL_STARTING_BALANCE, prices.bul_price())
MINIMUM_PAYMENT = int(os.environ.get('PAKET_MINIMUM_PAYMENT', 500))
BASIC_MONTHLY_ALLOWANCE = int(os.environ.get('PAKET_BASIC_MONTHLY_ALLOWANCE', 5000))


class FundLimitReached(Exception):
    """Unable to fund account because fund limit was reached."""


class NotEnoughInfo(Exception):
    """User does not provided enough information about himself."""


class InvalidVerificationCode(Exception):
    """User sent invalid or expired verification code."""


class InvalidPhoneNumber(Exception):
    """User provided invalid phone number."""


class PhoneNumberAlreadyInUse(Exception):
    """Specified phone number already in use by another user."""


class UnknownUser(Exception):
    """Requested user does not exist."""


class UserAlreadyExists(Exception):
    """User already exists."""


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
        sql.execute('''
            CREATE TABLE fundings(
                timestamp TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                user_pubkey VARCHAR(56) NOT NULL,
                currency VARCHAR(3),
                currency_amount BIGINT,
                euro_cents INTEGER,
                PRIMARY KEY (timestamp, user_pubkey),
                FOREIGN KEY(user_pubkey) REFERENCES users(pubkey))''')
        LOGGER.debug('fundings table created')


def request_verification_code(user_pubkey):
    """Send verification code to user's phone."""
    user_info = get_internal_user_infos(user_pubkey)

    if 'phone_number' not in user_info:
        raise NotEnoughInfo('phone number does not provided')
    if not get_test_result(user_pubkey, 'basic'):
        raise NotEnoughInfo('user does not passed KYC')

    parsed_phone_number = phonenumbers.parse(user_info['phone_number'])
    request = AUTHY_API.phones.verification_start(
        parsed_phone_number.national_number, parsed_phone_number.country_code, code_length=VERIFY_CODE_LENGTH)
    if not request.ok():
        raise authy.AuthyException(request.errors())


def check_verification_code(user_pubkey, verification_code):
    """
    Check verification code validity and create stellar account if it is not created yet.
    """
    user_info = get_internal_user_infos(user_pubkey)

    if 'phone_number' not in user_info:
        raise NotEnoughInfo('phone number does not provided')
    if not get_test_result(user_pubkey, 'basic'):
        raise NotEnoughInfo('user does not passed KYC')

    parsed_phone_number = phonenumbers.parse(user_info['phone_number'])
    verification = AUTHY_API.phones.verification_check(
        parsed_phone_number.national_number, parsed_phone_number.country_code, verification_code)

    if not verification.ok():
        raise InvalidVerificationCode('verification code invalid or expired')

    with SQL_CONNECTION() as sql:
        sql.execute("SELECT * FROM purchases WHERE user_pubkey = %s", (user_pubkey,))
        purchases = sql.fetchall()
    passed_kyc = get_test_result(user_pubkey, 'basic')
    if passed_kyc and not purchases:
        create_and_fund(user_pubkey)


def create_user(pubkey, call_sign):
    """Create a new user."""
    try:
        get_user(pubkey=pubkey)
    except UnknownUser:
        pass
    else:
        raise UserAlreadyExists(
            "user with provided pubkey ({}) already exists".format(pubkey))

    try:
        get_user(call_sign=call_sign)
    except UnknownUser:
        pass
    else:
        raise UserAlreadyExists(
            "user with provided call_sign ({}) already exists".format(call_sign))

    with SQL_CONNECTION() as sql:
        sql.execute("INSERT INTO users (pubkey, call_sign) VALUES (%s, %s)", (pubkey, call_sign.lower()))


def get_user(pubkey=None, call_sign=None):
    """Get user pubkey, call_sign, and purchase allowance from either pubkey or call_sign."""
    assert bool(pubkey or call_sign) != bool(pubkey and call_sign), 'specify either pubkey or call_sign'
    condition = ('pubkey', pubkey) if pubkey else ('call_sign', call_sign.lower())
    with SQL_CONNECTION() as sql:
        sql.execute("SELECT * FROM users WHERE {} = %s LIMIT 1".format(condition[0]), (condition[1],))
        try:
            return sql.fetchall()[0]
        except IndexError:
            raise UnknownUser("user with {} {} does not exists".format(*condition))


def get_callsings(call_sign_prefix=None):
    """Get registered call signs which starts with specified string."""
    with SQL_CONNECTION() as sql:
        if call_sign_prefix is not None and call_sign_prefix:
            sql.execute("SELECT * FROM users WHERE call_sign LIKE %s", (call_sign_prefix.lower() + '%',))
        else:
            sql.execute('SELECT * FROM users')
        return sql.fetchall()


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


def get_internal_user_infos(pubkey):
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


def get_user_infos(pubkey):
    """Get user infos, excluding sensitive data."""
    user_infos = get_internal_user_infos(pubkey)

    # place excluding code there

    return user_infos


def set_internal_user_info(pubkey, **kwargs):
    """Add optional details in local user info."""
    # Verify user exists.
    get_user(pubkey)

    user_details = get_internal_user_infos(pubkey)
    if kwargs:
        if 'phone_number' in kwargs:
            # validate and fix (if possible) phone number
            try:
                phone_number = phonenumbers.parse(kwargs['phone_number'])
                valid_number = phonenumbers.is_valid_number(phone_number)
                possible_number = phonenumbers.is_possible_number(phone_number)
                if not valid_number or not possible_number:
                    raise InvalidPhoneNumber('Invalid phone number')
                kwargs['phone_number'] = phonenumbers.format_number(
                    phone_number, phonenumbers.PhoneNumberFormat.E164)
            except phonenumbers.phonenumberutil.NumberParseException as exc:
                raise InvalidPhoneNumber("Invalid phone number. {}".format(str(exc)))

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


def get_monthly_allowance(pubkey):
    """Get a user's monthly allowance."""
    return BASIC_MONTHLY_ALLOWANCE if get_test_result(pubkey, 'basic') > 0 else 0


def get_monthly_expenses(pubkey):
    """Get a user's expenses in the last month."""
    with SQL_CONNECTION() as sql:
        sql.execute("""
            SELECT CAST(SUM(euro_cents) AS SIGNED) euro_cents FROM purchases
            WHERE user_pubkey = %s AND timestamp > %s AND paid > 1""", (
                pubkey, time.time() - (30 * 24 * 60 * 60)))
        try:
            return sql.fetchall()[0][b'euro_cents'] or 0
        except TypeError:
            return 0


def get_payment_address(user_pubkey, euro_cents, payment_currency, requested_currency):
    """Get an address to pay for a purchase."""
    assert payment_currency in ['BTC', 'ETH'], 'payment_currency must be BTC or ETH'
    assert requested_currency in ['BUL', 'XLM'], 'requested_currency must be BUL or XLM'
    remaining_monthly_allowance = get_monthly_allowance(user_pubkey) - get_monthly_expenses(user_pubkey)
    assert remaining_monthly_allowance >= int(euro_cents), \
        "{} is allowed to purchase up to {} euro-cents when {} are requested".format(
            user_pubkey, remaining_monthly_allowance, euro_cents)

    network = "btc{}".format('test' if DEBUG else '') if payment_currency.upper() == 'BTC' else 'ethereum'
    payment_pubkey = pywallet.wallet.create_address(network=network, xpub=XPUB)['address']
    set_purchase(user_pubkey, payment_pubkey, payment_currency, euro_cents, requested_currency)
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
    try:
        paket_stellar.get_bul_account(user_pubkey, accept_untrusted=True)
    except paket_stellar.stellar_base.address.AccountNotExistError:
        LOGGER.info("stellar account with pubkey %s does not exists and will be created", user_pubkey)
    else:
        LOGGER.info("stellar account with pubkey %s already exists", user_pubkey)
        return

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
    euro_cents = util.conversion.xlm_to_euro_cents(XLM_STARTING_BALANCE, prices.xlm_price())
    with SQL_CONNECTION() as sql:
        sql.execute("""
            INSERT INTO fundings (user_pubkey, currency, currency_amount, euro_cents)
            VALUES (%s, %s, %s, %s)""", (user_pubkey, 'XLM', XLM_STARTING_BALANCE, euro_cents))


def fund(user_pubkey):
    """Fund account with starting BUL amount."""
    funder_pubkey = paket_stellar.stellar_base.Keypair.from_seed(FUNDER_SEED).address().decode()
    prepare_fund_transaction = paket_stellar.prepare_send_buls(
        funder_pubkey, user_pubkey, BUL_STARTING_BALANCE)
    paket_stellar.submit_transaction_envelope(prepare_fund_transaction, FUNDER_SEED)
    euro_cents = util.conversion.bul_to_euro_cents(BUL_STARTING_BALANCE, prices.bul_price())
    with SQL_CONNECTION() as sql:
        sql.execute("""
            INSERT INTO fundings (user_pubkey, currency, currency_amount, euro_cents)
            VALUES (%s, %s, %s, %s)""", (user_pubkey, 'BUL', BUL_STARTING_BALANCE, euro_cents))


def get_unfunded():
    """Get new accounts that have not been funded yet."""
    with SQL_CONNECTION() as sql:
        sql.execute('''
            SELECT pubkey, call_sign FROM users
            WHERE pubkey NOT IN (SELECT user_pubkey FROM fundings WHERE currency = 'BUL') AND
            (SELECT result FROM test_results WHERE pubkey = pubkey AND name = 'basic'
            ORDER BY timestamp DESC LIMIT 1) = 1''')
        return sql.fetchall()


# pylint: disable=too-many-arguments
def set_purchase(user_pubkey, payment_pubkey, payment_currency, euro_cents, requested_currency, paid=0):
    """Add purchase info."""
    with SQL_CONNECTION() as sql:
        sql.execute('''
            INSERT INTO purchases (user_pubkey, payment_pubkey, payment_currency, euro_cents, requested_currency, paid)
            VALUES (%s, %s, %s, %s, %s, %s)''',
                    (user_pubkey, payment_pubkey, payment_currency, euro_cents, requested_currency, paid))
# pylint: enable=too-many-arguments


def get_purchases(paid_status=None):
    """Get all purchases or purchases with specified paid status."""
    if paid_status is not None:
        sql_query = '''
            SELECT payment_pubkey AS payment_address, purchases.* FROM purchases
            HAVING
                (SELECT paid FROM purchases WHERE payment_pubkey = payment_address ORDER BY timestamp DESC LIMIT 1) = %s
            AND paid = %s'''
    else:
        sql_query = 'SELECT * FROM purchases'
    with SQL_CONNECTION() as sql:
        sql.execute(sql_query, (paid_status, paid_status))
        return sql.fetchall()


def get_failed_purchases():
    """Get all failed purchases."""
    return get_purchases(paid_status=-1)


def get_unpaid_purchases():
    """Get all unpaid purchases."""
    return get_purchases(paid_status=0)


def get_paid_purchases():
    """Get all paid purchases."""
    return get_purchases(paid_status=1)


def get_completed_purchases():
    """Get all completed purchases."""
    return get_purchases(paid_status=2)


def get_current_purchases():
    """Get current status for all purchases."""
    with SQL_CONNECTION() as sql:
        sql.execute('''
            SELECT DISTINCT payment_pubkey AS payment_address, paid AS paid_status, purchases.* FROM purchases
            HAVING ((
                SELECT paid FROM purchases
                WHERE payment_pubkey = payment_address
                ORDER BY timestamp DESC LIMIT 1) = paid_status)''')
        return sql.fetchall()


def get_users():
    """Get list of users and their details - for debug only."""
    with SQL_CONNECTION() as sql:
        sql.execute('SELECT * FROM users')
        return {user['call_sign']: dict(
            get_user_infos(user['pubkey']),
            monthly_allowance=get_monthly_allowance(user['pubkey']),
            monthly_expenses=get_monthly_expenses(user['pubkey'])
        ) for user in sql.fetchall()}
