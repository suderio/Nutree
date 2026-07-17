#!/usr/bin/env python3

import csv
import sys

# Usage: ./csv2tsv.py < input.csv > output.tsv
if __name__ == "__main__":
    csv.writer(sys.stdout, dialect="excel-tab").writerows(
        csv.reader(sys.stdin, delimiter=";")
    )
