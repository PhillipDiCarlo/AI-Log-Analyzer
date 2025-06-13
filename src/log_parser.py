import re
from pathlib import Path
from collections import defaultdict
from typing import Dict, List
from datetime import datetime

# Define what constitutes a “problem” in your logs
ERROR_PATTERNS = [
    r"\berror\b",
    r"\bexception\b",
    r"\bfailed\b",
    r"\btimeout\b",
    r"\bsegfault\b"
]

# Regex for timestamps at the start of a line, e.g. "2025.06.13 01:23:38"
TS_PATTERN = re.compile(r"^(\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2})")

def is_problem(line: str) -> bool:
    """
    Return True if the line matches any of our error patterns.
    """
    return any(re.search(p, line, re.IGNORECASE) for p in ERROR_PATTERNS)

def parse_file(log_path: Path) -> Dict[str, int]:
    """
    Scan a single log file for problematic lines.
    Returns a dict mapping each unique problem line to its occurrence count.
    """
    counts: Dict[str, int] = defaultdict(int)
    with log_path.open(errors="ignore") as f:
        for line in f:
            if is_problem(line):
                counts[line.strip()] += 1
    return counts

def parse_file_with_timestamps(log_path: Path) -> List[datetime]:
    """
    Scan a log file for problematic lines and extract their timestamps.
    Returns a list of datetime objects (skips lines without a valid timestamp).
    """
    timestamps: List[datetime] = []
    with log_path.open(errors="ignore") as f:
        for line in f:
            if is_problem(line):
                m = TS_PATTERN.match(line)
                if m:
                    ts = datetime.strptime(m.group(1), "%Y.%m.%d %H:%M:%S")
                    timestamps.append(ts)
    return timestamps
