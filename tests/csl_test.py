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
            'oren', ' Oren ', 'oren Gampel',
            'osama', 'usama', 'bin laden, Usama', 'bin laden, osama', 'usama bin laden',
            'osama Tallal',
            'israel levin',
            'nationality',
            'KISHK egypt',
            'Ori Levi',
            'Babbar Khalsa',
            'Jose Maria', 'Jose naria', 'Jose Maria, SySOm', 'sison, Jose Maria', 'sisson, Jose Maria',
            'ANAYA MARTINEZ',
            'MAZIOTIS, Nikos',
            'TIERRA',
            'ABU FATIMA', 'AHMED THE EGYPTIAN',
            'ABDUL CHAUDHRY',
            'Ibrahim Issa Haji',
            'RICARDO PEREZ',
            'ABDUL GHANI',
            'AKHUNDZADA EHSANULLAH', 'MULLAH GUL AGHA',
            'vekselberg Victor'
        ]
        self.addresses = [
            'Juscelino Kubistcheck 338, 1802, Center, Foz do Iguacu, BR',
            'Piazza Giovane Italia, Varese, IT',
            'Carrera 43 A 7 50, Of. 302, Medellin, Antioquia, CO',
            'Al-Dawar Street, Bludan, SY',
            'Leipziger 64, Altenburg, 04600, DE',
            '144 Obolonska st., Kyiv, UA',
            '45 Nova st., Lviv, UA',
            '23 Fortechna st., Lugove, Rivne district, UA',
            '12 Snake st., Anaconda, PY',
            '164 Grande Rue, 92380 Garches, France',
            '18 Newlyn Ave, Maghull, Liverpool L31 6AX, UK',
            'Szeherezady 47, 60-101 Poznań, Poland',
            'Siming Qu, Xiamen Shi, Fujian Sheng, China',
            '130 Aberdare Rd, Shenton Park WA 6008, Australia',
            'Pje. Manuel Escalante 2687, Córdoba, Argentina',
            '343 Washington Ave, Winnipeg, MB R2K 1L7, CA'
        ]
        self.phones = [
            '+380671830125',
            '+380671830199',
            '+480927130239',
            '+131824537534',
            '+388005553535',
            '+942694211572',
            '+348326437765'
        ]

    def test_names(self):
        """Test names"""
        for name in self.names:
            score = self.csl.score_name(name)
            LOGGER.info("name: %s   score:%.2f", name, score)
