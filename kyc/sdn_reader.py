"""
Class that looks for a name in the OFAC SDN list:
https://www.treasury.gov/ofac/downloads/sdn.csv

The search is fuzzy, to allow for minor misspells.

details on the file:
https://www.treasury.gov/resource-center/sanctions/SDN-List/Documents/dat_spec.txt
"""
import csv
import requests
import os.path
import time

from fuzzywuzzy import fuzz


class SDNListChecker:
    all_rows = []
    filename = "SDN.CSV"
    url = 'https://www.treasury.gov/ofac/downloads/sdn.csv'

    def __init__(self):
        self.download_file()
        self.load_file()

    @classmethod
    def download_file(cls):
        """
        Download https://www.treasury.gov/ofac/downloads/sdn.csv locally to SDN.CSV
        only if the local file is old

        """
        try:
            creation_hours_ago = int(time.time() - os.path.getmtime(cls.filename)) / 3600
            print("current file is from %d hours" % creation_hours_ago)
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
            print("error loading %s, errror: %s" % (cls.url, e))


    @classmethod
    def load_file(cls):
        """
        Load a local SDN file.
        if not existing, load a new file from web.
        """
        FIELDNAMES = ("ent_num", "SDN_Name", "SDN_Type", "Program", "Title", "Call_Sign", "Vess_type", "Tonnage", "GRT",
                      "Vess_flag", "Vess_owner", "Remarks")
        with open(cls.filename, encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, fieldnames=FIELDNAMES, delimiter=',')
            for dict_row in reader:
                if dict_row['SDN_Type'] == "individual":
                    cls.all_rows.append(dict_row)
        print("loaded %d lines" % len(cls.all_rows))

    @classmethod
    def score_name(cls, name):
        """
        calculate risk score for a name
        :param name: name to look for. Order should be "Family Name, Surname"
        :return: score based on fuzzy search
        """
        top_score = 0.0
        for row in cls.all_rows:
            search_string = row['SDN_Name'] + " " + row['Remarks']
            ratio = fuzz.ratio(name.lower(), search_string.lower()) / 100
            partial_ratio = fuzz.partial_ratio(name.lower(), search_string.lower()) / 100

            # score is based on partial fuzzy search plus a small factor for full search
            fuzzy_score = min(1.0, partial_ratio + ratio / 5)
            if fuzzy_score > .6 and fuzzy_score > top_score:
                top_score = fuzzy_score
        return top_score ** 2


if __name__ == '__main__':
    sdn = SDNListChecker()
    NAMES = ["oren", " Oren ", "oren Gampel",
             "osama", "usama", "bin laden, Usama", "bin laden, osama", "usama bin laden",
             "osama Tallal",
             "israel levin",
             "nationality",
             "KISHK egypt",
             "Ori Levi",
             "Jose Maria", "Jose naria", "Jose Maria, SISON", "Jose Maria, SySOm", "sison, Jose Maria", "sisson, Jose Maria",
             ]

    for n in NAMES:
        score = sdn.score_name(n)
        print("n: %s   s:%.2f" % (n, score))
