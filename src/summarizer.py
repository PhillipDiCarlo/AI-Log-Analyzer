from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

def merge_counts(all_counts: Dict[str, int], new_counts: Dict[str, int]):
    """Add new_counts into all_counts in-place."""
    for line, cnt in new_counts.items():
        all_counts[line] = all_counts.get(line, 0) + cnt

def top_n_problems(counts: Dict[str, int], n: int = 10) -> List[Tuple[str, int]]:
    """Return the top n (line, count) sorted by count descending."""
    return Counter(counts).most_common(n)

def find_log_files(log_dir: Path) -> List[Path]:
    """Return a list of all .log files under log_dir."""
    return sorted(log_dir.glob("*.log"))
