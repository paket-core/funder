"""Routines for processing users purchases"""
import requests

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


def get_lumen_price(currency):
    """Get lumen price in BTC/ETH (satoshi or weis actually)"""
    assert currency in ['BTC', 'ETH'], 'currency must be BTC or ETH'
    digits = 10 ** 8 if currency == 'BTC' else 10 ** 18
    url = 'https://bb.otcbtc.com/api/v2/tickers/xlm{}'.format(currency.lower())
    response = requests.get(url)
    price = float(response.json()['ticker']['buy']) * digits
    return price


def get_currency_price(id_, convert):
    """
    Get crypto currency price in specified fiat currency.
    Crypto currency specifies as id from coinmarketcap.com
    """
    url = 'https://api.coinmarketcap.com/v2/ticker/{}/?convert={}'.format(id_, convert)
    response = requests.get(url)
    price = response.json()['data']['quotes'][convert]['price']
    return price


def get_btc_balance(address):
    """Get bitcoin address balance"""
    url = 'https://tchain.api.btc.com/v3/address/{}'.format(address)
    response = requests.get(url).json()
    if response['err_no'] == 0:
        return response['data']['balance']
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
    # multiply to 100 for getting price in euro_cents
    id_, digits = (BTC_ID, 10 ** 8) if currency == 'BTC' else (ETH_ID, 10 ** 18)
    # multiplying by 100 because we want to get price in euro cents
    price = get_currency_price(id_, 'EUR') * 100
    return amount * price / digits


def check_purchases_addresses():
    """Check purchases addresses and set paid status correspondingly to balance"""
    with db.SQL_CONNECTION() as sql:
        sql.execute("SELECT * FROM purchases WHERE paid = '0'")
        for purchase in sql.fetchall():
            LOGGER.info("checking address %s", purchase['payment_pubkey'])
            balance = get_balance(purchase['payment_pubkey'], purchase['payment_currency'])
            euro_cents_balance = currency_to_euro_cents(purchase['payment_currency'], int(balance))
            if euro_cents_balance >= db.MINIMUM_MONTHLY_ALLOWANCE:
                sql.execute("UPDATE purchases SET paid = '1' WHERE payment_pubkey = %s", (purchase['payment_pubkey'],))


def send_requested_currency():
    """Check purchases addresses with paid status and send requested currency to user account"""
    with db.SQL_CONNECTION() as sql:
        sql.execute("SELECT * FROM purchases WHERE paid = '1'")
        for purchase in sql.fetchall():
            balance = get_balance(purchase['payment_pubkey'], purchase['payment_currency'])
            euro_cents_balance = currency_to_euro_cents(purchase['payment_currency'], int(balance))
            monthly_allowance = db.get_monthly_allowance(purchase['user_pubkey'])
            monthly_expanses = db.get_monthly_expanses(purchase['user_pubkey'])
            remaining_monthly_allowance = monthly_allowance - monthly_expanses
            euro_to_charge = min(euro_cents_balance, remaining_monthly_allowance)
            if euro_to_charge:
                # TODO: place code for sending BULs or XLM to user accoutn here
                sql.execute("UPDATE purchases SET paid = '2' WHERE payment_pubkey = %s", (purchase['payment_pubkey'],))
