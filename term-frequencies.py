# Usage: python term_frequencies.py reddit_pre_covid_cleaned.xlsx \reddit_during_covid_cleaned.csv reddit_post_covid_cleaned.csv
# Author(s): Sarah Morrison-Smith (smorriso@hamilton.edu)
# Brief: Script for calculating term frequencies per 10,000 words in the full corpus (Appendix C).

import argparse
import re

import pandas as pd

TERMS = {
    "RTO, return/back to (the) office":
        r"\brto\b|return(?:ing)? to (?:the )?office|back to (?:the )?office",
    "Monitor, track, surveil, keylog, bossware, mouse jiggler":
        r"\bmonitor(?:ing|ed)?\b|\btrack(?:ing|ed)?\b|surveil|keylog|bossware|mouse ?jiggl|jiggler",
    "Camera, webcam":
        r"\bcameras?\b|\bwebcam",
    "Pay cut, salary, paid less, lower pay":
        r"pay ?cut|salary|paid less|lower pay",
    "Commute":
        r"\bcommut",
    "Childcare, daycare, kids, children, toddler":
        r"child ?care|daycare|\bkids?\b|\bchildren\b|toddler",
    "Lonely, isolated":
        r"lonel|isolat",
}
PERIODS = ["Pre-COVID", "COVID", "Post-COVID"]


def read_text(path):
    if path.endswith((".xlsx", ".xls")):
        d = pd.read_excel(path, usecols=["text"])
    else:
        d = pd.read_csv(path, usecols=["text"])
    return " ".join(d["text"].fillna("").astype(str).str.lower())


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("pre"); p.add_argument("covid"); p.add_argument("post")
    p.add_argument("-o", "--out", default="term_frequencies.csv")
    p.add_argument("--latex", action="store_true")
    a = p.parse_args()

    table = {}
    words = {}
    for period, path in zip(PERIODS, [a.pre, a.covid, a.post]):
        text = read_text(path)
        n = len(text.split())
        words[period] = n
        table[period] = {k: round(len(re.findall(v, text)) / n * 1e4, 1) for k, v in TERMS.items()}

    df = pd.DataFrame(table)
    df.loc["Total words (millions)"] = [round(words[p] / 1e6, 2) for p in PERIODS]
    df.to_csv(a.out)
    print(df.to_string())

    if a.latex:
        print()
        for term, row in df.iterrows():
            vals = " & ".join(f"{v:.2f}" if term.startswith("Total") else f"{v:.1f}" for v in row)
            print(f"    {term} & {vals} \\\\")


if __name__ == "__main__":
    main()