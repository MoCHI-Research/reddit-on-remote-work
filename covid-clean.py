# Usage: covid-clean <file_path>
# Author(s): Seth Moore (slmoore@hamilton.edu)
# Brief: This script will seperate the contents of a CSV file into 3 different files based on the COVID-19 timeline.
# The cutoffs being
# 2016 -> 2020
# 2020 -> May 8th, 2023
# May 8th, 2023 -> Present

import csv
import sys
from datetime import datetime
from pathlib import Path

EXPECTED_ARGUMENT_COUNT = 2
CSV_FIELD_NAMES = ['author', 'score', 'created', 'link', 'text']
CUTOFF_1 = datetime.strptime("2016-01-01", "%Y-%m-%d")
CUTOFF_2 = datetime.strptime("2020-01-01", "%Y-%m-%d")
CUTOFF_3 = datetime.strptime("2023-05-08", "%Y-%m-%d")

def create_csv_dict_reader(file_path : str):
    file = open(file_path, encoding='utf8', mode='r')
    return csv.DictReader(file)

def create_csv_dict_writer(file_path : str):
    file = open(file_path, encoding='utf8', mode='w')
    return csv.DictWriter(file, fieldnames=CSV_FIELD_NAMES)

if __name__ == '__main__':
    if len(sys.argv) != EXPECTED_ARGUMENT_COUNT:
        print("usage: covid-clean [file_path]")
    
    file_path = sys.argv[1]

    pre_covid_file_path = Path(file_path).stem + "_pre_covid.csv"
    during_covid_file_path = Path(file_path).stem + "_during_covid.csv"
    post_covid_file_path = Path(file_path).stem + "_post_covid.csv"

    csv_reader = create_csv_dict_reader(file_path)
    pre_covid_csv_writer = create_csv_dict_writer(pre_covid_file_path)
    during_covid_csv_writer = create_csv_dict_writer(during_covid_file_path)
    post_covid_csv_writer = create_csv_dict_writer(post_covid_file_path)

    pre_covid_csv_writer.writeheader()
    during_covid_csv_writer.writeheader()
    post_covid_csv_writer.writeheader()

    fields = next(csv_reader)

    print(fields)

    for row in csv_reader:
        date = datetime.strptime(row['created'], "%Y-%m-%d %H:%M")

        if date < CUTOFF_1:
            # Ignore this data
            #print(f"{date} is before the first cutoff")
            pass
        
        if (date >= CUTOFF_1) and (date < CUTOFF_2):
            # This is where you should write to pre-covid CSV files
            #print(f"{date} is pre-covid")
            pre_covid_csv_writer.writerow(row)
        
        if (date >= CUTOFF_2) and (date < CUTOFF_3):
            # This is where you should write to during-covid CSV files
            #print(f"{date} is during covid")
            during_covid_csv_writer.writerow(row)
        
        if (date >= CUTOFF_3):
            # This is where you should write to post-covid CSV files
            #print(f"{date} is post-covid")
            post_covid_csv_writer.writerow(row)
