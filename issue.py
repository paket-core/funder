#!/usr/bin/env python3
"""Issue BULs."""
import os

import paket_stellar
import util.logger

LOGGER = util.logger.logging.getLogger('pkt.issue')
DEBUG = True
TOTAL_SUPPLY = 10**9 * 10**7
ISSUER_KEYPAIR = paket_stellar.get_keypair(seed=os.environ['ISSUER_SEED'])
DISTRIBUTOR_KEYPAIR = paket_stellar.get_keypair(seed=os.environ['DISTRIBUTOR_SEED'])


def issue(issuer_keypair, distributor_keypair, total_supply):
    """Issue tokens to distributor."""
    paket_stellar.submit_transaction_envelope(
        paket_stellar.prepare_trust(distributor_keypair.address()),
        distributor_keypair.seed())
    paket_stellar.submit_transaction_envelope(
        paket_stellar.prepare_send_buls(issuer_keypair.address(), distributor_keypair.address(), total_supply),
        issuer_keypair.seed())


def kill_issuer(issuer_keypair):
    """Set issuer's master_weight to zero, to ensure no new BULs can be ever minted."""
    builder = paket_stellar.gen_builder(issuer_keypair.address())
    builder.append_set_options_op(master_weight=0)
    paket_stellar.submit_transaction_envelope(builder.gen_te().xdr(), issuer_keypair.seed())


if __name__ == '__main__':
    util.logger.setup()
    issue(ISSUER_KEYPAIR, DISTRIBUTOR_KEYPAIR, TOTAL_SUPPLY)
    if not DEBUG:
        kill_issuer(ISSUER_KEYPAIR)
