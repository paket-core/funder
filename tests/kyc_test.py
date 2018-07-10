"""Tests for kyc module"""
import unittest

import util.logger

import kyc


LOGGER = util.logger.logging.getLogger('pkt.funder.test')


class KYCTest(unittest.TestCase):

    def test_scammer(self):
        """Test kyc result on scammer's data"""
        name = 'Youssef Ben Abdul Baki Ben Youcef'
        address = 'Piazza Giovane Italia n.2, Varese, IT'
        phone = ''
        result = kyc.basic_kyc(name, address, phone)
        self.assertEqual(result, 0, "scammer passed kyc")

    def test_fair(self):
        """Test kyc on fair person's data"""
        name = 'Sherlock Holmes'
        address = '221b Baker Street, London, UK'
        phone = '+44 20 7487 3372'
        result = kyc.basic_kyc(name, address, phone)
        self.assertEqual(result, 1, 'fair user does not pass kyc')

    def test_partial(self):
        """Test kyc on partial available info"""
        scammers_partial_info = [
            {
                'name':'Youssef Ben Abdul',
                'address':'',
                'phone': ''
            },
            {
                'name': '',
                'address': 'Piazza Giovane Italia n.2, Varese, IT',
                'phone': '+82 20 7727 3112'
            }
        ]
        for scammer in scammers_partial_info:
            with self.subTest(**scammer):
                result = kyc.basic_kyc(**scammer)
                self.assertEqual(result, 0)
