"""Test identitymind interface."""
import unittest
import identitymind
from identity import LOGGER

LOGGER.setLevel('INFO')


class IdentityMindTest(unittest.TestCase):
    """Test IdentityMind."""
    def test_trusted(self):
        """Test a trusted identity."""
        kyc_request = identitymind.request_kyc(man='man', bfn="Tom", bln="ed", bc="Zetroit", stage="3")
        LOGGER.debug(kyc_request)
        for field in ['tid', 'user', 'res', 'rcd', 'state']:
            LOGGER.info("%s: %s", field, kyc_request.get(field))

        self.assertEqual(kyc_request['user'], 'TRUSTED')

    def test_suspicious(self):
        """Test a suspicious identity."""
        kyc_request = identitymind.request_kyc(man='man', bfn="Sue", bln="ed", bc="Zetroit", stage="3")
        LOGGER.debug(kyc_request)
        for field in ['tid', 'user', 'res', 'rcd', 'state']:
            LOGGER.info("%s: %s", field, kyc_request.get(field))

        self.assertEqual(kyc_request['user'], 'SUSPICIOUS')


if __name__ == '__main__':
    unittest.main()
