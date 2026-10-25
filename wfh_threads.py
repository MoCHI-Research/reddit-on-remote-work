# Author(s): Sarah Morrison-Smith (smorriso@hamilton.edu)
# Brief: Thread-level analysis helpers for the Reddit WFH paper.

import argparse
import csv
import re
import sqlite3
import sys

import pandas as pd

# ---------------------------------------------------------------- MAXQDA
# MAXQDA 24 project files are SQLite databases. Rows are versioned by
# transaction (TID), so we keep the newest version of each row and drop
# rows marked for deletion. Document text is encrypted, but document names,
# the code tree, and which document each coded segment belongs to are not.

def _latest(con, table, cols):
    q = (f"select {cols}, TID, ToDelete from {table} t "
         f"where TID = (select max(TID) from {table} u where u.ID = t.ID)")
    return [r for r in con.execute(q).fetchall() if r[-1] == 0]


def load_mx(path):
    con = sqlite3.connect(path)
    texts = {r[0]: r[1] for r in _latest(con, "Texts", "ID, Name")}
    codes = {r[0]: {"parent": r[1], "name": r[2], "idx": r[3]}
             for r in _latest(con, "Codewords", "ID, WordID, Name, Idx")}
    codings = [{"text": r[0], "code": r[1]}
               for r in _latest(con, "Codings", "TextID, WordID")
               if r[0] in texts and r[1] in codes]
    return texts, codes, codings


def thread_ids_from_mx(path):
    """MAXQDA document names look like 't3_abc123 (thread title)'."""
    texts, _, _ = load_mx(path)
    return {name.split(" ")[0].replace("t3_", "") for name in texts.values()}


# ---------------------------------------------------------------- data
def read_export(path):
    """Read a cleaned export (.csv or .xlsx) with columns id, author, created, link, text."""
    if path.endswith((".xlsx", ".xls")):
        d = pd.read_excel(path)
    else:
        d = pd.read_csv(path, usecols=lambda c: c in {"id", "author", "score", "created", "link", "text"})
    d["text"] = d["text"].fillna("").astype(str)
    # Posts and comments share the thread id in their permalink.
    d["thread"] = d["link"].astype(str).str.extract(r"/comments/([a-z0-9]+)/")[0]
    return d


def read_sample(path):
    d = pd.read_csv(path)
    d["text"] = d["text"].fillna("").astype(str)
    return d


def titles(sample):
    first = sample.sort_values("created").groupby("thread").head(1)
    return {r.thread: r.text.split("\n")[0][:80] for r in first.itertuples()}


# ---------------------------------------------------------------- commands
def cmd_extract(a):
    ids = thread_ids_from_mx(a.mx)
    d = read_export(a.export)
    s = d[d.thread.isin(ids)]
    missing = ids - set(s.thread)
    s.to_csv(a.out, index=False)
    n = s.groupby("thread").size() - 1
    print(f"{s.thread.nunique()} of {len(ids)} threads found; {len(s)} rows; "
          f"{n.sum()} comments; median {n.median()}; largest {n.max()}")
    if missing:
        print("not found in export:", sorted(missing), file=sys.stderr)


def cmd_dump(a):
    s = read_sample(a.sample)
    with open(a.out, "w") as f:
        for th, g in sorted(s.groupby("thread"), key=lambda x: x[1].created.min()):
            g = g.sort_values("created")
            f.write(f"\n######## {th} | {str(g.iloc[0].created)[:10]} | {len(g) - 1} comments\n")
            for i, r in enumerate(g.itertuples()):
                f.write(("OP: " if i == 0 else "- ") + re.sub(r"\s+", " ", r.text).strip() + "\n")
    print("wrote", a.out)


def cmd_search(a):
    s = read_sample(a.sample)
    t = titles(s)
    flags = 0 if a.case else re.I
    skip = set(a.skip.split(",")) if a.skip else set()
    n = 0
    for th, g in s.groupby("thread"):
        if th in skip:
            continue
        hits = []
        for txt in g.text:
            for m in re.finditer(a.pattern, txt, flags):
                lo = max(0, m.start() - a.context)
                hits.append(txt[lo:m.end() + a.context].replace("\n", " "))
        if hits:
            n += 1
            print(f"== t3_{th} | {t[th]} | {len(hits)} hits")
            for h in hits[:a.max]:
                print("   ..", h)
    print("threads with hits:", n)


def cmd_codes(a):
    texts, codes, codings = load_mx(a.mx)

    def desc(c):
        out = {c}
        for k, v in codes.items():
            if v["parent"] == c:
                out |= desc(k)
        return out

    def walk(parent, depth):
        kids = sorted((k for k, v in codes.items() if v["parent"] == parent), key=lambda k: codes[k]["idx"])
        for k in kids:
            d = desc(k)
            n = len({x["text"] for x in codings if x["code"] in d})
            print("  " * depth + f"{codes[k]['name']}  ({n} threads incl. subcodes)")
            walk(k, depth + 1)

    coded = {x["text"] for x in codings}
    print(f"{len(texts)} documents, {len(coded)} with at least one code, {len(codes)} codes")
    for r in {v["parent"] for v in codes.values()} - set(codes):
        walk(r, 0)


def cmd_counts(a):
    samples = {}
    for path in a.samples:
        s = read_sample(path)
        samples[path] = (set(s.thread), titles(s))
    rows = []
    with open(a.claims) as f:
        for c in csv.DictReader(f):
            ids = c["thread_ids"].split()
            # Find the sample that contains these threads (one file per period).
            match = [p for p, (have, _) in samples.items() if set(ids) <= have]
            if not match:
                sys.exit(f"claim '{c['claim']}' lists threads not in any sample: {ids}")
            t = samples[match[0]][1]
            rows.append({"period": c["period"], "section": c["section"], "claim": c["claim"],
                         "n_threads": len(ids),
                         "threads": "; ".join(f"t3_{i}: {t[i]}" for i in ids)})
    pd.DataFrame(rows).to_csv(a.out, index=False)
    for r in rows:
        print(f"{r['period']:6s} {r['section']:6s} {r['n_threads']:3d}  {r['claim']}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("extract"); s.add_argument("mx"); s.add_argument("export"); s.add_argument("out")
    s.set_defaults(f=cmd_extract)
    s = sub.add_parser("dump"); s.add_argument("sample"); s.add_argument("out"); s.set_defaults(f=cmd_dump)
    s = sub.add_parser("search"); s.add_argument("sample"); s.add_argument("pattern")
    s.add_argument("--case", action="store_true", help="case-sensitive")
    s.add_argument("--skip", help="comma-separated thread ids to leave out")
    s.add_argument("--context", type=int, default=110, help="characters shown around each match")
    s.add_argument("--max", type=int, default=5, help="matches shown per thread")
    s.set_defaults(f=cmd_search)
    s = sub.add_parser("codes"); s.add_argument("mx"); s.set_defaults(f=cmd_codes)
    s = sub.add_parser("counts"); s.add_argument("claims"); s.add_argument("samples", nargs="+")
    s.add_argument("-o", "--out", default="thread_counts.csv"); s.set_defaults(f=cmd_counts)

    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
