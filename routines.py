"""Routines for processing users purchases"""
import sys

import requests

import paket_stellar
import util.conversion
import util.logger

import db

LOGGER = util.logger.logging.getLogger('pkt.funder.routines')
# one euro cent costs 0.1 BUL (1000000 stroops)
BULS_PER_EURO = 1000000
ETHERSCAN_API_KEY = '6KYNDD61K9YA9CX1NWUPVWCVFJN24K9QV5'
# currencies ids on coinmarketcap.com
XLM_ID = 512
ETH_ID = 1027
BTC_ID = 1


class BalanceError(Exception):
    """Can't get balance for specified address"""


def get_currency_price(id_, convert):
    """
    Get crypto currency price in specified fiat currency.
    Crypto currency specifies as id from coinmarketcap.com
    """
    url = 'https://api.coinmarketcap.com/v2/ticker/{}/?convert={}'.format(id_, convert)
    response = requests.get(url)
    price = response.json()['data']['quotes'][convert]['price']
    # we need to cast to string because API returns price as float number
    return str(price)


def get_btc_balance(address):
    """Get bitcoin address balance"""
    url = 'https://tchain.api.btc.com/v3/address/{}'.format(address)
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
    url = 'https://api-ropsten.etherscan.io/api'
    response = requests.get(url, params=params).json()
    if response['message'] == 'OK':
        return int(response['result'])
    raise BalanceError(response['result'])


def get_balance(address, network):
    """Get balance of address in specified network"""
    return get_btc_balance(address) if network == 'BTC' else get_eth_balance(address)


def currency_to_euro_cents(currency, amount):
    """Convert amount of coins in specified currency to euro cents"""
    assert currency in ['BTC', 'ETH'], 'currency must be BTC or ETH'
    id_, decimals = (BTC_ID, util.conversion.BTC_DECIMALS) if currency == 'BTC' else (
        ETH_ID, util.conversion.ETH_DECIMALS)
    eur_price = get_currency_price(id_, 'EUR')
    price_decimals = len(eur_price.split('.')[1])
    # price in fictitious units (portions of euro cents) by 1 indivisible unit of specified crypto currency
    fictitious_units_price = util.conversion.divisible_to_indivisible(eur_price, price_decimals)
    fictitious_units_amount = fictitious_units_price * amount
    # minus two because initial price was in EUR and we want euro cents
    euro_cents = util.conversion.indivisible_to_divisible(fictitious_units_amount, price_decimals + decimals - 2)
    LOGGER.warning("precision loss: %s converted to %s", euro_cents, round(float(euro_cents)))
    # integer part of result will be amount of euro cents
    return round(float(euro_cents))


def euro_cents_to_stroops(euro_cents_amount):
    """Convert amount of euro cents to stroops"""
    eur_price = get_currency_price(XLM_ID, 'EUR')
    price_decimals = len(eur_price.split('.')[1])
    fictitious_units_amount = util.conversion.divisible_to_indivisible(
        euro_cents_amount, util.conversion.STELLAR_DECIMALS + price_decimals)
    fictitious_units_price = util.conversion.divisible_to_indivisible(eur_price, price_decimals + 2)
    stroops = fictitious_units_amount // fictitious_units_price
    LOGGER.warning("precision loss: %s / %s = %s", fictitious_units_amount, fictitious_units_price, stroops)
    return stroops


def fund_account(user_pubkey, amount, asset_code):
    """Fund account with XLM or BUL"""
    assert asset_code in ['XLM', 'BUL'], 'asset must be XLM or BUL'
    prepare_function = paket_stellar.prepare_send_buls if asset_code == 'BUL' else paket_stellar.prepare_send_lumens
    prepared_transaction = prepare_function(paket_stellar.ISSUER, user_pubkey, amount)
    paket_stellar.submit_transaction_envelope(prepared_transaction, paket_stellar.ISSUER_SEED)


def create_new_account(user_pubkey, amount):
    """Create new Stellar account and send specified amount of XLM to it"""
    prepared_transaction = paket_stellar.prepare_create_account(paket_stellar.ISSUER, user_pubkey, amount)
    paket_stellar.submit_transaction_envelope(prepared_transaction, paket_stellar.ISSUER_SEED)


def check_purchases_addresses():
    """Check purchases addresses and set paid status correspondingly to balance"""
    purchases = db.get_unpaid()
    for purchase in purchases:
        LOGGER.info("checking address %s", purchase['payment_pubkey'])
        balance = get_balance(purchase['payment_pubkey'], purchase['payment_currency'])
        euro_cents_balance = currency_to_euro_cents(purchase['payment_currency'], balance)
        if euro_cents_balance >= db.MINIMUM_MONTHLY_ALLOWANCE:
            db.update_purchase(purchase['payment_pubkey'], 1)


def send_requested_currency():
    """Check purchases addresses with paid status and send requested currency to user account"""
    purchases = db.get_paid()
    for purchase in purchases:
        balance = get_balance(purchase['payment_pubkey'], purchase['payment_currency'])
        euro_cents_balance = currency_to_euro_cents(purchase['payment_currency'], balance)
        monthly_allowance = db.get_monthly_allowance(purchase['user_pubkey'])
        monthly_expanses = db.get_monthly_expanses(purchase['user_pubkey'])
        remaining_monthly_allowance = monthly_allowance - monthly_expanses
        euro_to_fund = min(euro_cents_balance, remaining_monthly_allowance)
        if euro_to_fund:
            if purchase['requested_currency'] == 'BUL':
                fund_amount = euro_to_fund * BULS_PER_EURO
                try:
                    account = paket_stellar.get_bul_account(purchase['user_pubkey'])
                    if account['bul_balance'] + fund_amount <= account['bul_limit']:
                        fund_account(purchase['user_pubkey'], fund_amount, 'BUL')
                        LOGGER.info("%s funded with %s BUL", purchase['user_pubkey'], fund_amount)
                        db.update_purchase(purchase['payment_pubkey'], 2)
                    else:
                        LOGGER.error("account %s need to set higher limit for BUL."
                                     " balance: %s limit: %s amount to fund: %s", purchase['user_pubkey'],
                                     account['bul_balance'], account['bul_limit'], fund_amount)
                        db.update_purchase(purchase['payment_pubkey'], -1)
                except (paket_stellar.TrustError, paket_stellar.stellar_base.exceptions.AccountNotExistError) as exc:
                    LOGGER.error(str(exc))
                    db.update_purchase(purchase['payment_pubkey'], -1)
            else:
                fund_amount = euro_cents_to_stroops(euro_to_fund)
                try:
                    paket_stellar.get_bul_account(purchase['user_pubkey'], accept_untrusted=True)
                    fund_account(purchase['user_pubkey'], fund_amount, 'XLM')
                    LOGGER.info("%s funded with %s XLM", purchase['user_pubkey'], fund_amount)
                except paket_stellar.stellar_base.address.AccountNotExistError:
                    LOGGER.info("account %s does not exist and will be created", purchase['user_pubkey'])
                    create_new_account(purchase['user_pubkey'], fund_amount)
                db.update_purchase(purchase['payment_pubkey'], 2)


if __name__ == '__main__':
    util.logger.setup()
    try:
        if sys.argv[1] == 'monitor':
            check_purchases_addresses()
            sys.exit(0)
        if sys.argv[1] == 'pay':
            send_requested_currency()
            sys.exit(0)
    except IndexError:
        pass
    print(' Usage: python routines.py [monitor|pay]')
