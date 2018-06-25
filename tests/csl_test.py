"""Tests for csl_reader module"""
import unittest

import util.logger

import csl_reader


LOGGER = util.logger.logging.getLogger('pkt.funder.test')


class ClsReaderTest(unittest.TestCase):
    """Tests for csl_reader module"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.csl = csl_reader.CSLListChecker()
        self.names = [
            "oren", " Oren ", "oren Gampel",
            "osama", "usama", "bin laden, Usama", "bin laden, osama", "usama bin laden",
            "osama Tallal",
            "israel levin",
            "nationality",
            "KISHK egypt",
            "Ori Levi",
            "Babbar Khalsa",
            "Jose Maria", "Jose naria", "Jose Maria, SySOm", "sison, Jose Maria", "sisson, Jose Maria",
            "ANAYA MARTINEZ",
            "MAZIOTIS, Nikos",
            "TIERRA",
            "ABU FATIMA", "AHMED THE EGYPTIAN",
            "ABDUL CHAUDHRY",
            "Ibrahim Issa Haji",
            "RICARDO PEREZ",
            "ABDUL GHANI",
            "AKHUNDZADA EHSANULLAH", "MULLAH GUL AGHA",
            "vekselberg Victor"
        ]

    def test_names(self):
        """Test names"""
        for name in self.names:
            score = self.csl.score_name(name)
            LOGGER.info("name: %s   score:%.2f [%s]", name, score[0], score[1])
