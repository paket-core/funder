"""Test identitymind interface."""
import unittest
from pprint import pprint

import identitymind

LOGGER = identitymind.LOGGER
LOGGER.setLevel('INFO')


class IdentityMindTest(unittest.TestCase):
    """Test IdentityMind."""
    def test_playing(self):

        kyc_post = identitymind.request_kyc(man='man', bfn="Tom", bsn="1520", profile='new', bco='USA', sco='USA')
        print_result(kyc_post)
        # kyc_get = identitymind.get_kyc_status(kyc_post['tid'])
        # LOGGER.debug(kyc_get)
        # for f in ['tid', 'user', 'res', 'rcd', 'state', 'ednaScoreCard']:
        #     LOGGER.info("%s: %s", f, kyc_get.get(f))

        self.assertEqual(kyc_post['state'], 'A')

    def test_current_reputation(self):
        """
        check the `user` field. Can be managed in sandbox via the `bfn` parameter.
        """
        for val, resp in [
            ('Tom', 'TRUSTED'),
            ('Sue', 'SUSPICIOUS'),
            ('Brad', 'BAD'),
            ('someone', 'UNKNOWN')
        ]:
            LOGGER.warning("man='man called {}', bfn=val, bln='ed'".format(val))
            kyc_request = identitymind.request_kyc(man='man called {}'.format(val), bfn=val, bln="ed")
            print_result(kyc_request)
            self.assertEqual(kyc_request['user'], resp)

    def test_policy_result(self):
        """
        check the `state` field. Can be managed in sandbox via the `bc` parameter.
        """
        for val, resp in [
            ('Detroit', 'D'),
            ('Monte Rio', 'R'),
            ('someone', 'A')
        ]:
            kyc_request = identitymind.request_kyc(man='man from {}'.format(val), bc=val)
            print_result(kyc_request)
            self.assertEqual(kyc_request['state'], resp)


def print_result(kyc_result):
    LOGGER.debug(kyc_result)
    for f in ['tid', 'user', 'res', 'rcd', 'state', 'ednaScoreCard']:
        # pprint(kyc_result)
        LOGGER.info("%s: %s", f, kyc_result.get(f))


if __name__ == '__main__':
    unittest.main()
