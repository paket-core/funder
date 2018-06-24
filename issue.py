#!/usr/bin/env python3
"""Issue BULs."""
import os

import requests
import stellar_base.address
import stellar_base.asset
import stellar_base.builder
import stellar_base.keypair

import util.logger

DEBUG = True

util.logger.setup()
LOGGER = util.logger.logging.getLogger('pkt.issue')


def get_details(address):
    """Get account details."""
    details = stellar_base.address.Address(address.decode(), horizon=HORIZON)
    details.get()
    return details


def submit(builder):
    """Submit a transaction."""
    response = builder.submit()
    if 'status' in response and response['status'] >= 300:
        LOGGER.error("tx failed: %s", response)
        raise Exception(response)
    LOGGER.debug(response)
    return response


def issue(issuer_keypair, distributor_keypair, asset_code, total_supply):
    """Issue tokens to distributor."""
    LOGGER.info("%s extending trust to %s (%s)", distributor_keypair, asset_code, issuer_keypair)
    builder = stellar_base.builder.Builder(horizon=HORIZON, secret=distributor_keypair.seed())
    builder.append_trust_op(issuer_keypair.address().decode(), asset_code)
    builder.sign()
    submit(builder)
    LOGGER.info('trust extended')

    LOGGER.info("sending %s %ss from %s to %s", total_supply, asset_code, issuer_keypair, distributor_keypair)
    builder = stellar_base.builder.Builder(horizon=HORIZON, secret=issuer_keypair.seed())
    builder.append_payment_op(
        distributor_keypair.address().decode(), total_supply, asset_code, issuer_keypair.address().decode())
    builder.add_text_memo('issuance')
    builder.append_set_options_op(home_domain='paket.global')
    builder.sign()
    submit(builder)
    LOGGER.info("distributor %s should now be funded", distributor_keypair)


if __name__ == '__main__':
    if DEBUG:
        HORIZON = 'https://horizon-testnet.stellar.org'

        def get_account(seed=None):
            """Get an account or create a new one."""
            keypair = stellar_base.keypair.Keypair.from_seed(
                seed if seed else stellar_base.keypair.Keypair.random().seed())
            keypair.__class__ = type('DisplayKeypair', (stellar_base.keypair.Keypair,), {
                '__repr__': lambda self: "KeyPair (pubkey:{}, seed:{})".format(self.address(), self.seed())})
            if seed is None:
                LOGGER.debug("creating and funding account %s (%s)", keypair, keypair.seed())
                request = requests.get("https://friendbot.stellar.org/?addr={}".format(keypair.address().decode()))
                if request.status_code != 200:
                    LOGGER.error("Request to friendbot failed: %s", request.json())
            return keypair

        ISSUER = get_account(os.environ.get('ISSUER_SEED'))
        DISTRIBUTOR = get_account(os.environ.get('DISTRIBUTOR_SEED'))

    else:
        raise NotImplementedError('The issuance script can not currently be run outside of debug mode.')

    ISSUER_DETAILS, DISTRIBUTOR_DETAILS = [get_details(keypair.address()) for keypair in [ISSUER, DISTRIBUTOR]]
    LOGGER.info("ISSUER is: %s with balances: %s", ISSUER_DETAILS.address, ISSUER_DETAILS.balances)
    LOGGER.info("DISTRIBUTOR is: %s with balances: %s", DISTRIBUTOR_DETAILS.address, DISTRIBUTOR_DETAILS.balances)

    issue(ISSUER, DISTRIBUTOR, 'BUL', 1000)

    ISSUER_DETAILS, DISTRIBUTOR_DETAILS = [get_details(keypair.address()) for keypair in [ISSUER, DISTRIBUTOR]]
    LOGGER.info("ISSUER is: %s with balances: %s", ISSUER_DETAILS.address, ISSUER_DETAILS.balances)
    LOGGER.info("DISTRIBUTOR is: %s with balances: %s", DISTRIBUTOR_DETAILS.address, DISTRIBUTOR_DETAILS.balances)
