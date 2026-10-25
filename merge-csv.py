# Usage: merge-csv <file_paths> <file>
# Author(s): Anonymized for Review
# Brief: Script for merging multiple csv files

import csv
import sys
import glob
from pathlib import Path

def write_csv(csv : csv.DictWriter):
    pass

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("usage: merge-csv <file_paths> <file>")
    
    csvwriter = csv.DictWriter(
        fieldnames=['author', 'score', 'created', 'link', 'text'], # You may want to change this when going between submissions and comments
        f=open(file=sys.argv[2], encoding='utf8', mode='w'))

    print("Merging the following files...")
    print(glob.glob(sys.argv[1]))

    csvwriter.writeheader()
    
    for file_path in glob.glob(sys.argv[1]):
        csvreader = csv.DictReader(f=open(file=file_path, encoding='utf8', mode='r'))
        
        for row in csvreader:
            csvwriter.writerow(row)