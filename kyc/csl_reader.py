"""
Class that looks for a name in the Consolidated Screening List:
https://2016.export.gov/ecr/eg_main_023148.asp

The search is fuzzy, to allow for minor misspells.

details on the file:
build.export.gov/build/idcplg?IdcService=DOWNLOAD_PUBLIC_FILE&RevisionSelectionMethod=Latest&dDocName=eg_main_040971
"""
import csv
import requests
import os.path
import time

from fuzzywuzzy import fuzz


class CSLListChecker:
    all_rows = []
    filename = "CSL.CSV"
    url = 'https://api.trade.gov/consolidated_screening_list/search.csv?api_key=OHZYuksFHSFao8jDXTkfiypO'

    def __init__(self):
        self.download_file()
        self.load_file()

    @classmethod
    def download_file(cls):
        """
        Download csv locally 
        only if the local file is old

        """
        try:
            creation_hours_ago = int(time.time() - os.path.getmtime(cls.filename)) / 3600
            print("current file is from %d hours ago" % creation_hours_ago)
            if creation_hours_ago < 24:
                print("no need to load new version")
                return
        except FileNotFoundError:
            print("Local file '%s' not found" % cls.filename)

        try:
            response = requests.get(cls.url)
            # Throw an error for bad status codes
            response.raise_for_status()
            with open(cls.filename, 'wb') as handle:
                for block in response.iter_content(1024):
                    handle.write(block)
        except Exception as e:
            print("error loading %s, error: %s" % (cls.url, e))

        print(open(cls.filename, 'r'))

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
        for row in cls.all_rows:
            search_string = row['name'] + " " + row['alt_names']
            ratio = fuzz.ratio(name.lower(), search_string.lower()) / 100
            partial_ratio = fuzz.partial_ratio(name.lower(), search_string.lower()) / 100

            # score is based on partial fuzzy search plus a small factor for full search
            fuzzy_score = min(1.0, .95*partial_ratio + ratio / 5)
            if fuzzy_score > .6 and fuzzy_score > top_score:
                # print("SC: %.2f %.2f n:%s str:%s" % (partial_ratio, ratio, name, search_string))
                top_score = fuzzy_score
                comment = "name:{} - aka:{}  program:{}".format(row['name'], row['alt_names'], row['programs'])
        # print("n:%s str:%s" % (name, search_string))
        return top_score ** 2, comment


if __name__ == '__main__':
    csl = CSLListChecker()
    NAMES = ["oren", " Oren ", "oren Gampel",
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
             "AKHUNDZADA EHSANULLAH", "MULLAH GUL AGHA"
             ]

    for n in NAMES:
        score = csl.score_name(n)
        print("n: %s   s:%.2f [%s]" % (n, score[0], score[1]))
