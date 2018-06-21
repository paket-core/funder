"""Routines for processing users purchases"""
import requests

import util.logger

import db


LOGGER = util.logger.logging.getLogger('pkt.funder.MODULENAME')
# using USD now because price of EUR is unavailable
EUR_ASSET_CODE = 'USD'
EUR_ISSUER = 'GBUYUAI75XXWDZEKLY66CFYKQPET5JR4EENXZBUZ3YXZ7DS56Z4OKOFU'
# currencies ids on coinmarketcap.com
XLM_ID = 512
ETH_ID = 1027
BTC_ID = 1


def get_lumen_price(currency):
    """Get lumen price in BTC/ETH (satoshi or weis actually)"""
    assert currency in ['BTC', 'ETH'], 'currency must be BTC or ETH'
    digits = 10 ** 8 if currency == 'BTC' else 10 ** 18
    url = 'https://bb.otcbtc.com/api/v2/tickers/xlm{}'.format(currency.lower())
    response = requests.get(url)
    price = float(response.json()['ticker']['buy']) * digits
    return price


def get_euro_asset_price():
    """Get euro asset price in XLM"""
    url = 'https://api.stellar.expert/api/explorer/public/asset/{}-{}'.format(EUR_ASSET_CODE, EUR_ISSUER)
    response = requests.get(url)
    price = response.json()['price_dynamic'][0][1]
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
    url = 'https://chain.api.btc.com/v3/address/{}'.format(address)
    response = requests.get(url)
    return response.json()['data']['balance']


def get_eth_balance(address):
    """Get ethereum address balance"""
    url = 'https://api.etherscan.io/api?module=account&action=balance&address={}&tag=latest'.format(address)
    response = requests.get(url)
    return response.json()['result']


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
        sql.execute('SELECT * FROM purchases WHERE paid = 0')
        for purchase in sql.fetchall():
            balance = get_balance(purchase['payment_pubkey'], purchase['payment_currency'])
            euro_cents_balance = currency_to_euro_cents(purchase['payment_currency'], int(balance))
            # xlm_price = get_lumen_price(purchase['payment_currency'])
            # euro_asset_price = get_euro_asset_price()
            # xlm_amount = balance / xlm_price
            # euro_cents_balance = xlm_amount / euro_asset_price

            if euro_cents_balance >= purchase['euro_cents']:
                sql.execute("UPDATE purchases SET paid = '1' WHERE payment_pubkey = %s", (purchase['payment_pubkey']))
