# Usage:
# python ctat_topics.py topics pre_covid.mta -o topics_pre.csv
# python ctat_topics.py sample pre_covid.mta
# python ctat_topics.py topics path/to/folder    # folder holding Datasets/ and Samples/

# Author(s): Sarah Morrison-Smith (smorriso@hamilton.edu)
# Brief: Topic tables and sample statistics from a saved CTAT workspace (Appendix B, Table 1).

import argparse
import glob
import io
import os
import pickle
import statistics
import sys
import tarfile
from collections import Counter

import pandas as pd

TRUSTED_MODULES = {"builtins", "collections", "datetime", "copyreg", "_codecs", "numpy"}


class _Obj:
    """Stand-in for CTAT classes: keeps the object's attributes, nothing else."""
    def __init__(self, *a, **k):
        pass

    def __setstate__(self, state):
        if isinstance(state, dict):
            self.__dict__.update(state)
        else:
            self.__dict__["_state"] = state


class _Unpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if module.split(".")[0] in TRUSTED_MODULES:
            return super().find_class(module, name)
        return type(name, (_Obj,), {"__module__": module})


def _unpickle(data):
    return _Unpickler(io.BytesIO(data)).load()


def load_workspace(path):
    """Return (dataset, {sample_name: sample}) from a .mta file or a folder
    containing CTAT's Datasets/ and Samples/ folders."""
    if os.path.isdir(path):
        ds_files = glob.glob(os.path.join(path, "Datasets", "*.pk"))
        if len(ds_files) != 1:
            sys.exit(f"expected one dataset in {path}/Datasets, found {len(ds_files)}")
        with open(ds_files[0], "rb") as f:
            dataset = _unpickle(f.read())
        samples = {}
        for sp in glob.glob(os.path.join(path, "Samples", "*", "sample.pk")):
            with open(sp, "rb") as f:
                s = _unpickle(f.read())
            samples[getattr(s, "_name", sp)] = s
        return dataset, samples
    with tarfile.open(path) as tar:
        members = {m.name.lstrip("./"): m for m in tar.getmembers() if m.isfile()}
        ds_names = [n for n in members if n.startswith("Datasets/") and n.endswith(".pk")]
        if len(ds_names) != 1:
            sys.exit(f"expected one dataset in the workspace, found {len(ds_names)}")
        dataset = _unpickle(tar.extractfile(members[ds_names[0]]).read())
        samples = {}
        for n in members:
            if n.startswith("Samples/") and n.endswith("/sample.pk"):
                s = _unpickle(tar.extractfile(members[n]).read())
                samples[getattr(s, "_name", n)] = s
    return dataset, samples


def pick_sample(samples, name):
    if name:
        return samples[name]
    if len(samples) != 1:
        sys.exit(f"workspace has several models {list(samples)}; choose one with --model")
    return next(iter(samples.values()))


def topic_rows(sample):
    cutoff = sample._document_cutoff
    probs = sample._document_topic_prob          # {doc key: {topic: probability}}
    counts = Counter(t for p in probs.values() for t, v in p.items() if v >= cutoff)
    rows = []
    for topic, part in sample.parts_dict.items():
        if topic == "unknown":
            continue
        words = part._word_list                   # [(word, weight), ...]
        rows.append({"topic": topic,
                     "threads": counts[topic],
                     "keywords": ", ".join(w for w, _ in words),
                     "weights": ", ".join(f"{float(x):.4f}" for _, x in words)})
    rows.sort(key=lambda r: r["topic"])
    return rows, len(probs), cutoff


def cmd_topics(a):
    dataset, samples = load_workspace(a.workspace)
    s = pick_sample(samples, a.model)
    rows, modeled, cutoff = topic_rows(s)
    print(f"model {s._name}: {s._num_topics} topics, {modeled} threads modeled, cutoff {cutoff}")
    df = pd.DataFrame(rows)
    print(df[["topic", "threads", "keywords"]].to_string(index=False))
    if a.out:
        df.to_csv(a.out, index=False)
        print("wrote", a.out)


def cmd_sample(a):
    dataset, samples = load_workspace(a.workspace)
    s = pick_sample(samples, a.model)
    keys = [dataset.documents[u]._doc_id for u in s.selected_documents]
    data = [dataset._data[k] for k in keys]
    comments = [len(d["csv.text"]) - 1 for d in data]          # csv.text = [post, comment, ...]
    subs = Counter(str(d["url"]).split("/r/")[1].split("/")[0].lower() for d in data)
    per_topic = Counter(t for k in keys for t, v in s._document_topic_prob[k].items()
                        if v >= s._document_cutoff)
    print(f"threads {len(keys)}  comments {sum(comments)}  median {statistics.median(comments)}  "
          f"largest {max(comments)}")
    print("by subreddit:", dict(subs))
    print("selected per topic:", dict(sorted(per_topic.items())))
    if a.ids:
        with open(a.ids, "w") as f:
            f.write("\n".join(k[-1] for k in keys) + "\n")
        print("wrote thread ids to", a.ids)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, f in [("topics", cmd_topics), ("sample", cmd_sample)]:
        s = sub.add_parser(name)
        s.add_argument("workspace", help="CTAT .mta file, or a folder with Datasets/ and Samples/")
        s.add_argument("--model", help="model name, if the workspace has several")
        s.set_defaults(f=f)
    sub.choices["topics"].add_argument("-o", "--out", help="write the table to this CSV")
    sub.choices["sample"].add_argument("--ids", help="write the selected thread ids to this file")
    a = p.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()