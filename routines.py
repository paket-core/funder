"""Routines for processing users purchases"""
import os
import sys

import requests

import paket_stellar
import util.logger

import db
import simulation

LOGGER = util.logger.logging.getLogger('pkt.funder.routines')
DEBUG = bool(os.environ.get('PAKET_DEBUG'))
FUNDER_SEED = os.environ['PAKET_FUNDER_SEED']
ETHERSCAN_API_KEY = os.environ['PAKET_ETHERSCAN_API_KEY']


class BalanceError(Exception):
    """Can't get balance for specified address"""


def get_btc_balance(address):
    """Get bitcoin address balance"""
    url = 'https://{testnet}chain.api.btc.com/v3/address/{address}'.format(
        address=address, testnet='t' if DEBUG else '')
    response = requests.get(url).json()
    if response['err_no'] == 0:
        return response['data']['balance'] if response['data'] is not None else 0
    raise BalanceError(response['err_msg'])


def get_eth_balance(address):
    """Get ethereum address balance"""
    params = {
        'module': 'account',
        'action': 'balance',
        'address': address,
        'tag': 'latest',
        'apikey': ETHERSCAN_API_KEY
    }
    url = "https://api{testnet}.etherscan.io/api".format(testnet='-ropsten' if DEBUG else '')
    response = requests.get(url, params=params).json()
    if response['message'] == 'OK':
        return int(response['result'])
    raise BalanceError(response['result'])


def get_balance(address, network):
    """Get balance of address in specified network"""
    return get_btc_balance(address) if network == 'BTC' else get_eth_balance(address)


def fund_account(user_pubkey, amount, asset_code):
    """Fund account with XLM or BUL"""
    assert asset_code in ['XLM', 'BUL'], 'asset must be XLM or BUL'
    prepare_function = paket_stellar.prepare_send_buls if asset_code == 'BUL' else paket_stellar.prepare_send_lumens
    prepared_transaction = prepare_function(paket_stellar.ISSUER, user_pubkey, amount)
    paket_stellar.submit_transaction_envelope(prepared_transaction, FUNDER_SEED)


def create_new_account(user_pubkey, amount):
    """Create new Stellar account and send specified amount of XLM to it"""
    prepared_transaction = paket_stellar.prepare_create_account(paket_stellar.ISSUER, user_pubkey, amount)
    paket_stellar.submit_transaction_envelope(prepared_transaction, FUNDER_SEED)


def add_trust(user_pubkey, user_seed):
    """Add BUL trust to account."""
    prepared_transaction = paket_stellar.prepare_trust(user_pubkey)
    paket_stellar.submit_transaction_envelope(prepared_transaction, seed=user_seed)


def check_purchases_addresses():
    """Check purchases addresses and set paid status correspondingly to balance"""
    purchases = db.get_unpaid_purchases()
    for purchase in purchases:
        LOGGER.info("checking address %s", purchase['payment_pubkey'])
        balance = get_balance(purchase['payment_pubkey'], purchase['payment_currency'])
        conversion_function, price = (db.util.conversion.btc_to_euro_cents, db.prices.btc_price()) \
            if purchase['payment_currency'].upper() == 'BTC' \
            else (db.util.conversion.eth_to_euro_cents, db.prices.eth_price())
        euro_cents_balance = conversion_function(balance, price)
        if euro_cents_balance >= db.MINIMUM_PAYMENT:
            db.set_purchase(
                purchase['user_pubkey'], purchase['payment_pubkey'], purchase['payment_currency'],
                purchase['euro_cents'], purchase['requested_currency'], paid=1)


def send_requested_currency():
    """Check purchases addresses with paid status and send requested currency to user account."""
    purchases = db.get_paid_purchases()
    for purchase in purchases:
        balance = get_balance(purchase['payment_pubkey'], purchase['payment_currency'])
        conversion_function, price = (db.util.conversion.btc_to_euro_cents, db.prices.btc_price()) \
            if purchase['payment_currency'].upper() == 'BTC' \
            else (db.util.conversion.eth_to_euro_cents, db.prices.eth_price())
        euro_cents_balance = conversion_function(balance, price)
        monthly_allowance = db.get_monthly_allowance(purchase['user_pubkey'])
        monthly_expanses = db.get_monthly_expanses(purchase['user_pubkey'])
        remaining_monthly_allowance = monthly_allowance - monthly_expanses
        euro_to_fund = min(euro_cents_balance, remaining_monthly_allowance)
        if euro_to_fund:
            if purchase['requested_currency'] == 'BUL':
                fund_amount = db.util.conversion.euro_cents_to_bul_stroops(
                    euro_to_fund, db.prices.bul_price())
                try:
                    account = paket_stellar.get_bul_account(purchase['user_pubkey'])
                    if account['bul_balance'] + fund_amount <= account['bul_limit']:
                        fund_account(purchase['user_pubkey'], fund_amount, 'BUL')
                        LOGGER.info("%s funded with %s BUL", purchase['user_pubkey'], fund_amount)
                        db.set_purchase(
                            purchase['user_pubkey'], purchase['payment_pubkey'], purchase['payment_currency'],
                            purchase['euro_cents'], purchase['requested_currency'], paid=2)
                    else:
                        LOGGER.error("account %s need to set higher limit for BUL."
                                     " balance: %s limit: %s amount to fund: %s", purchase['user_pubkey'],
                                     account['bul_balance'], account['bul_limit'], fund_amount)
                        db.set_purchase(
                            purchase['user_pubkey'], purchase['payment_pubkey'], purchase['payment_currency'],
                            purchase['euro_cents'], purchase['requested_currency'], paid=-1)
                except (paket_stellar.TrustError, paket_stellar.stellar_base.exceptions.AccountNotExistError) as exc:
                    LOGGER.error(str(exc))
                    db.set_purchase(
                        purchase['user_pubkey'], purchase['payment_pubkey'], purchase['payment_currency'],
                        purchase['euro_cents'], purchase['requested_currency'], paid=-1)
            else:
                fund_amount = db.util.conversion.euro_cents_to_xlm_stroops(
                    euro_to_fund, db.prices.xlm_price())
                try:
                    paket_stellar.get_bul_account(purchase['user_pubkey'], accept_untrusted=True)
                    fund_account(purchase['user_pubkey'], fund_amount, 'XLM')
                    LOGGER.info("%s funded with %s XLM", purchase['user_pubkey'], fund_amount)
                except paket_stellar.stellar_base.address.AccountNotExistError:
                    LOGGER.info("account %s does not exist and will be created", purchase['user_pubkey'])
                    create_new_account(purchase['user_pubkey'], fund_amount)
                db.set_purchase(
                    purchase['user_pubkey'], purchase['payment_pubkey'], purchase['payment_currency'],
                    purchase['euro_cents'], purchase['requested_currency'], paid=2)


def fund_new_accounts():
    """Check new accounts and fund them with BULs."""
    unfunded_users = db.get_unfunded()
    if not unfunded_users:
        LOGGER.info('there is no new users with unfunded accounts')
        return

    daily_spent = db.get_daily_spent_euro()
    hourly_spent = db.get_hourly_spent_euro()
    remaining_funds = min(
        db.HOURLY_FUND_LIMIT - hourly_spent if db.HOURLY_FUND_LIMIT > hourly_spent else 0,
        db.DAILY_FUND_LIMIT - daily_spent if db.DAILY_FUND_LIMIT > daily_spent else 0)

    if remaining_funds == 0:
        LOGGER.warning('unable to fund, fund limit reached')
        LOGGER.warning("hourly spent amount: %s; daily spent amount: %s", hourly_spent, daily_spent)

    for index, user in enumerate(unfunded_users):
        funded_users_amount = index
        if funded_users_amount * db.EUR_BUL_STARTING_BALANCE >= remaining_funds:
            LOGGER.warning(
                "fund limit reached; %s accounts funded, %s accounts remaining",
                funded_users_amount, len(unfunded_users) - funded_users_amount)
            break
        # pylint:disable=broad-except
        try:
            db.fund(user['pubkey'])
            LOGGER.info("user %s (%s) funded with %s BUL",
                        user['pubkey'], user['call_sign'], db.BUL_STARTING_BALANCE)
        except Exception as exc:
            LOGGER.warning(str(exc))
        # pylint:enable=broad-except


if __name__ == '__main__':
    util.logger.setup()
    try:
        if sys.argv[1] == 'monitor':
            check_purchases_addresses()
        elif sys.argv[1] == 'pay':
            send_requested_currency()
        elif sys.argv[1] == 'fund':
            fund_new_accounts()
        elif sys.argv[1] == 'simulate_launcher':
            simulation.simulation_routine('launcher')
        elif sys.argv[1] == 'simulate_courier':
            simulation.simulation_routine('courier')
        elif sys.argv[1] == 'simulate_recipient':
            simulation.simulation_routine('recipient')
        sys.exit(0)
    except IndexError:
        pass
    print(' Usage: python routines.py [monitor|pay|fund|simulate_launcher|simulate_courier|simulate_recipient]')
