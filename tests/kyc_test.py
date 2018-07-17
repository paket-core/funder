"""Tests for kyc module"""
import unittest

import util.logger

import kyc


LOGGER = util.logger.logging.getLogger('pkt.funder.test')


class KYCTest(unittest.TestCase):
    """Test KYC functionality."""

    def test_scammer(self):
        """Test kyc result on scammer's data"""
        name = 'Youssef Ben Abdul Baki'
        result = kyc.basic_kyc(name)
        self.assertEqual(result, 0, "scammer passed kyc")

    def test_fair(self):
        """Test kyc on fair person's data"""
        name = 'Sherlock Holmes'
        result = kyc.basic_kyc(name)
        self.assertEqual(result, 1, 'fair user does not pass kyc')
