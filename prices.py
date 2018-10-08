"""Prices of currencies."""
import os

import requests

BUL_PRICE = os.environ['PAKET_BUL_PRICE']
MARKET_URL_FORMAT = 'https://api.coinmarketcap.com/v2/ticker/{}/?convert={}'

# currencies ids on coinmarketcap.com
BTC_ID = 1
ETH_ID = 1027
XLM_ID = 512


def get_currency_price(id_, convert='EUR'):
    """
    Get crypto currency price in specified fiat currency.
    Crypto currency specifies as id from coinmarketcap.com
    :param id_: Currency id on coinmarketcap.com
    :param convert: Name of fiat currency
    :return: Amount of specified fiat currency by one unit of specified crypto currency
    """
    url = MARKET_URL_FORMAT.format(id_, convert)
    response = requests.get(url)
    price = response.json()['data']['quotes'][convert]['price']
    # we need to cast to string because API returns price as float number
    return str(price)


def btc_price():
    """Get BTC price in EUR."""
    return get_currency_price(BTC_ID)


def eth_price():
    """Get ETH price in EUR."""
    return get_currency_price(ETH_ID)


def xlm_price():
    """Get XLM price in EUR."""
    return get_currency_price(XLM_ID)


def bul_price():
    """Get BUL price in EUR."""
    return BUL_PRICE
