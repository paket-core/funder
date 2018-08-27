"""Currency conversions"""
import os

import requests

import util.conversion
import util.logger

LOGGER = util.logger.logging.getLogger('pkt.funder.routines')
BUL_STROOPS_FOR_EUR_CENT = int(os.environ['PAKET_BUL_STROOPS_FOR_EUR_CENT'])
MARKET_URL_FORMAT = 'https://api.coinmarketcap.com/v2/ticker/{}/?convert={}'
# currencies ids on coinmarketcap.com
XLM_ID = 512
ETH_ID = 1027
BTC_ID = 1


def get_currency_price(id_, convert):
    """
    Get crypto currency price in specified fiat currency.
    Crypto currency specifies as id from coinmarketcap.com
    """
    url = MARKET_URL_FORMAT.format(id_, convert)
    response = requests.get(url)
    price = response.json()['data']['quotes'][convert]['price']
    # we need to cast to string because API returns price as float number
    return str(price)


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


def euro_cents_to_xlm_stroops(euro_cents_amount):
    """Convert amount of euro cents to stroops"""
    eur_price = get_currency_price(XLM_ID, 'EUR')
    price_decimals = len(eur_price.split('.')[1])
    fictitious_units_amount = util.conversion.divisible_to_indivisible(
        euro_cents_amount, util.conversion.STELLAR_DECIMALS + price_decimals)
    fictitious_units_price = util.conversion.divisible_to_indivisible(eur_price, price_decimals + 2)
    stroops = fictitious_units_amount // fictitious_units_price
    LOGGER.warning("precision loss: %s / %s = %s", fictitious_units_amount, fictitious_units_price, stroops)
    return stroops


def euro_cents_to_bul_stroops(euro_cents_amount):
    """Convert amount of euro cents to BUL stroops"""
    return euro_cents_amount * BUL_STROOPS_FOR_EUR_CENT
