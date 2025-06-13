from pathlib import Path
from src.summarizer import merge_counts, top_n_problems, find_log_files
import pandas as pd

def test_merge_and_top_n():
    all_counts = {"a": 3, "b": 1}
    new_counts = {"a": 2, "c": 5}
    merge_counts(all_counts, new_counts)
    # now a:5, b:1, c:5
    top = top_n_problems(all_counts, n=2)
    # should pick the two highest counts
    assert set(x[0] for x in top) == {"a", "c"}

def test_find_log_files(tmp_path):
    # create some .log files and some other
    (tmp_path/"one.log").write_text("")
    (tmp_path/"two.LOG").write_text("")
    (tmp_path/"ignore.txt").write_text("")
    files = find_log_files(tmp_path)
    assert len(files) == 2
    assert all(f.suffix.lower() == ".log" for f in files)
