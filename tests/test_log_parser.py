import re
from pathlib import Path
from src.log_parser import is_problem, parse_file, parse_file_with_timestamps
from datetime import datetime

def test_is_problem_true():
    assert is_problem("2025.06.13 12:00:00 ERROR: something bad happened")
    assert is_problem("Exception thrown in module")
    assert is_problem("failed to connect")

def test_is_problem_false():
    assert not is_problem("All systems operational")
    assert not is_problem("INFO: startup complete")

def test_parse_file(tmp_path):
    # create a fake log file
    content = "\n".join([
        "INFO: ok line",
        "ERROR: boom",
        "Warning: minor issue",
        "ERROR: boom"
    ])
    p = tmp_path / "sample.log"
    p.write_text(content)

    counts = parse_file(p)
    # should only count lines containing “error” or “Warning” (case-insensitive)
    assert counts["ERROR: boom"] == 2
    assert counts["Warning: minor issue"] == 1
    assert "INFO: ok line" not in counts

def test_parse_file_with_timestamps(tmp_path):
    content = "\n".join([
        "2025.06.13 12:00:00 ERROR: boom",
        "2025.06.13 12:01:00 Info: skip",
        "2025.06.13 12:02:00 Exception: fail"
    ])
    p = tmp_path / "ts.log"
    p.write_text(content)

    timestamps = parse_file_with_timestamps(p)
    # should parse two datetimes
    assert timestamps == [
        datetime(2025, 6, 13, 12, 0, 0),
        datetime(2025, 6, 13, 12, 2, 0)
    ]
