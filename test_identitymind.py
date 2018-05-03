import unittest
import identitymind
from identity import LOGGER

LOGGER.setLevel('INFO')


class MyTestCase(unittest.TestCase):
    def test_trusted(self):
        kyc_request = identitymind.call(identitymind.POST, '', man='man', bfn="Tom", bln="ed", bc="Zetroit", stage="3")
        LOGGER.debug(kyc_request)
        for f in ['tid', 'user', 'res', 'rcd', 'state']:
            LOGGER.info("%s: %s", f, kyc_request.get(f))

        self.assertEqual(kyc_request['user'], 'TRUSTED')

    def test_suspicious(self):
        kyc_request = identitymind.call(identitymind.POST, '', man='man', bfn="Sue", bln="ed", bc="Zetroit", stage="3")
        LOGGER.debug(kyc_request)
        for f in ['tid', 'user', 'res', 'rcd', 'state']:
            LOGGER.info("%s: %s", f, kyc_request.get(f))

        self.assertEqual(kyc_request['user'], 'SUSPICIOUS')


if __name__ == '__main__':
    unittest.main()
