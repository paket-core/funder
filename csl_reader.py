"""
Class that looks for a name in the Consolidated Screening List:
https://2016.export.gov/ecr/eg_main_023148.asp

The search is fuzzy, to allow for minor misspells.

details on the file:
build.export.gov/build/idcplg?IdcService=DOWNLOAD_PUBLIC_FILE&RevisionSelectionMethod=Latest&dDocName=eg_main_040971
"""
import csv
import os.path
import time

import fuzzywuzzy.fuzz
import requests

import util.logger
import util.countly

util.logger.setup()
LOGGER = util.logger.logging.getLogger('pkt.funder.csl')


class CSLListChecker:
    """
    List checker.
    """
    all_rows = []
    filename = "CSL.CSV"
    url = 'https://api.trade.gov/consolidated_screening_list/search.csv?api_key=OHZYuksFHSFao8jDXTkfiypO'

    def __init__(self):
        self.download_file()
        self.load_file()

    @classmethod
    def download_file(cls):
        """
        Download csv locally only if the local file is old
        """
        try:
            creation_hours_ago = int(time.time() - os.path.getmtime(cls.filename)) / 3600
            LOGGER.info("current file is from %d hours ago", creation_hours_ago)
            if creation_hours_ago < 24:
                LOGGER.info("no need to load new version")
                return
        except FileNotFoundError:
            LOGGER.info("Local file '%s' not found", cls.filename)

        # pylint: disable=broad-except
        # Still testing.
        try:
            util.countly.send_countly_event('download csl', 0)
            response = requests.get(cls.url)
            # Throw an error for bad status codes
            response.raise_for_status()
            with open(cls.filename, 'wb') as handle:
                for block in response.iter_content(1024):
                    handle.write(block)
            util.countly.send_countly_event('download csl', 1, end_session=1)
        except Exception as exception:
            LOGGER.warning("error loading %s, error: %s", cls.url, exception)

        LOGGER.info(open(cls.filename, 'r'))
        # pylint: enable=broad-except

    @classmethod
    def load_file(cls):
        """
        Load a local CSL file.
        if not existing, load a new file from web.
        """
        with open(cls.filename, encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=',')
            for dict_row in reader:
                if dict_row['type'] == "Individual":
                    cls.all_rows.append(dict_row)
        LOGGER.info("loaded %d lines", len(cls.all_rows))
        LOGGER.info(cls.all_rows[1].keys())

    @classmethod
    def score(cls, search_query, *search_rows):
        """
        calculate risk score for a given search_query - from 0 (no fit) to 1 (match found).
        :param search_query: words to look for.
        :param search_rows: names of rows to search in
        :return: score based on fuzzy search
        """
        top_score = 0.0
        programs = ''
        for row in cls.all_rows:
            search_string = ' '.join([row[row_name] for row_name in search_rows])
            ratio = fuzzywuzzy.fuzz.ratio(search_query.lower(), search_string.lower()) / 100
            partial_ratio = fuzzywuzzy.fuzz.partial_ratio(search_query.lower(), search_string.lower()) / 100

            # score is based on partial fuzzy search plus a small factor for full search
            fuzzy_score = min(1.0, .95 * partial_ratio + ratio / 5)
            if fuzzy_score > .6 and fuzzy_score > top_score:
                # print("SC: %.2f %.2f n:%s str:%s" % (partial_ratio, ratio, name, search_string))
                top_score = fuzzy_score
                programs = str(row['programs'])
        final_score = top_score ** 2
        if final_score > .95:
            util.countly.send_countly_event('KYC_verify', 1, programs=programs, result='flagged')
        elif final_score > .85:
            util.countly.send_countly_event('KYC_verify', 1, programs=programs, result='suspicious')
        else:
            util.countly.send_countly_event('KYC_verify', 1, result='pass', hour=17)
        return final_score

    @classmethod
    def score_name(cls, name):
        """
        calculate risk score for a name - from 0 (no fit) to 1 (name found).
        :param name: name to look for. Order should be "Family Name, Surname"
        :return: score based on fuzzy search
        """
        return cls.score(name, 'name', 'alt_names')

    @classmethod
    def score_address(cls, address):
        """
        calculate risk score for an address - from 0 (no fit) to 1 (address found).
        :param address: address to look for.
        :return: score based on fuzzy search
        """
        return cls.score(address, 'addresses')

    @classmethod
    def score_phone(cls, phone):
        """
        calculate risk score for an phone number - from 0 (no fit) to 1 (phone number found).
        :param phone: phone to look for
        :return: score based on fuzzy search
        """
        # it is just mock-up
        return .5
