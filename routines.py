"""Routines for processing users purchases"""
import requests

import util.conversion
import util.logger

import db


LOGGER = util.logger.logging.getLogger('pkt.funder.routines')
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
        return response['result']
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
    fictitious_units_price = util.conversion.divisible_to_indivisible(
        eur_price, price_decimals, numeric_representation=True)
    euro_cents = fictitious_units_price * amount
    # minus two because initial price was in EUR and we want euro cents
    euro_cents = util.conversion.indivisible_to_divisible(
        euro_cents, price_decimals + decimals - 2, numeric_representation=True)
    # integer part of result will be amount of euro cents
    return int(euro_cents)


def check_purchases_addresses():
    """Check purchases addresses and set paid status correspondingly to balance"""
    purchases = db.get_unpaid()
    for purchase in purchases:
        LOGGER.info("checking address %s", purchase['payment_pubkey'])
        balance = get_balance(purchase['payment_pubkey'], purchase['payment_currency'])
        euro_cents_balance = currency_to_euro_cents(purchase['payment_currency'], int(balance))
        if euro_cents_balance >= db.MINIMUM_MONTHLY_ALLOWANCE:
            db.update_purchase(purchase['payment_pubkey'], 1)


def send_requested_currency():
    """Check purchases addresses with paid status and send requested currency to user account"""
    purchases = db.get_paid()
    for purchase in purchases:
        balance = get_balance(purchase['payment_pubkey'], purchase['payment_currency'])
        euro_cents_balance = currency_to_euro_cents(purchase['payment_currency'], int(balance))
        monthly_allowance = db.get_monthly_allowance(purchase['user_pubkey'])
        monthly_expanses = db.get_monthly_expanses(purchase['user_pubkey'])
        remaining_monthly_allowance = monthly_allowance - monthly_expanses
        euro_to_charge = min(euro_cents_balance, remaining_monthly_allowance)
        if euro_to_charge:
            # TODO: place code for sending BULs or XLM to user accoutn here
            db.update_purchase(purchase['payment_pubkey'], 2)
