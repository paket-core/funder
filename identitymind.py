"""Interact with IdentityMind's edna."""
import json
import requests

import util.logger

HOST = 'https://sandbox.identitymind.com'
USER = 'paket'
PASS = 'XXX'
LOGGER = util.logger.logging.getLogger('pkt.funder.identitymind')

util.logger.setup()


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
