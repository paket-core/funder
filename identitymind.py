#!/usr/bin/env python3
"""Play with edna."""
import json
import requests

import logger

HOST = 'https://sandbox.identitymind.com'
USER = 'paket'
PASS = 'XXX'
LOGGER = logger.logging.getLogger('pkt.identity')

logger.setup()


def call(method, endpoint, host, user, password, **kwargs):
    """Call identitymind API."""
    data = json.dumps(kwargs) if kwargs else None
    uri = "{}{}".format(host, endpoint)
    req = method(uri, auth=(user, password), data=data)

    try:
        assert req.status_code < 300, "call to <{}> failed with status {} ({})".format(
            endpoint, req.status_code, req.text)
    except AssertionError as exception:
        LOGGER.exception(str(exception))
        import pprint
        LOGGER.debug("data is: %s", pprint.pformat(kwargs))
        LOGGER.debug("request is: %s", pprint.pformat(vars(req)))
        raise

    return req.json()


def request_kyc(host=HOST, user=USER, password=PASS, **kwargs):
    """Request KYC verification."""
    return call(requests.post, '/im/account/consumer/', host, user, password, **kwargs)


def get_kyc_status(transaction_id, host=HOST, user=USER, password=PASS):
    """Check KYC verification status and results."""
    return call(requests.get, "/im/account/consumer/{}".format(transaction_id), host, user, password)


if __name__ == '__main__':
    KYC_REQUEST = request_kyc(man='man', bfn="Sue", bln="ed", bc="Zetroit", stage="3")
    LOGGER.debug(KYC_REQUEST)
    for f in ['tid', 'user', 'res', 'rcd', 'state']:
        LOGGER.info("%s: %s", f, KYC_REQUEST.get(f))

    KYC_STATUS = get_kyc_status(KYC_REQUEST['tid'])
    LOGGER.debug(KYC_STATUS)
    for f in ['tid', 'user', 'res', 'rcd', 'state']:
        LOGGER.info("%s: %s", f, KYC_STATUS.get(f))
