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
            print("current file is from %d hours ago" % creation_hours_ago)
            if creation_hours_ago < 24:
                print("no need to load new version")
                return
        except FileNotFoundError:
            print("Local file '%s' not found" % cls.filename)

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
            print("error loading %s, error: %s" % (cls.url, exception))

        print(open(cls.filename, 'r'))
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
        print("loaded %d lines" % len(cls.all_rows))
        print(cls.all_rows[1].keys())

    @classmethod
    def score_name(cls, name):
        """
        calculate risk score for a name - from 0 (no fit) to 1 (name found).
        :param name: name to look for. Order should be "Family Name, Surname"
        :return: score based on fuzzy search
        """
        top_score = 0.0
        comment = ''
        programs = ''
        for row in cls.all_rows:
            search_string = row['name'] + " " + row['alt_names']
            ratio = fuzzywuzzy.fuzz.ratio(name.lower(), search_string.lower()) / 100
            partial_ratio = fuzzywuzzy.fuzz.partial_ratio(name.lower(), search_string.lower()) / 100

            # score is based on partial fuzzy search plus a small factor for full search
            fuzzy_score = min(1.0, .95 * partial_ratio + ratio / 5)
            if fuzzy_score > .6 and fuzzy_score > top_score:
                # print("SC: %.2f %.2f n:%s str:%s" % (partial_ratio, ratio, name, search_string))
                top_score = fuzzy_score
                comment = "name:{} - aka:{}  program:{}".format(row['name'], row['alt_names'], row['programs'])
                programs = str(row['programs'])
        final_score = top_score ** 2
        if final_score > .95:
            util.countly.send_countly_event('KYC_verify', 1, programs=programs, result='flagged')
        elif final_score > .85:
            util.countly.send_countly_event('KYC_verify', 1, programs=programs, result='suspicious')
        else:
            util.countly.send_countly_event('KYC_verify', 1, result='pass', hour=17)
        return final_score, comment
