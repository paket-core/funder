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


def call(method, endpoint, host=HOST, user=USER, password=PASS, **kwargs):
    """Call identitymind API."""
    data = json.dumps(kwargs) if kwargs else None
    uri = "{}/im/account/consumer{}".format(host, endpoint)
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


KYC_REQUEST = call(requests.post, '', man='bob', bfn='bob')
LOGGER.info(KYC_REQUEST)
KYC_STATUS = call(requests.get, "/{}".format(KYC_REQUEST['tid']))
LOGGER.info(KYC_STATUS)
