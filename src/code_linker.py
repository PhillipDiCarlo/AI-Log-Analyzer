import re
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

def extract_keywords(error: str, min_length: int = 4, max_keywords: int = 3) -> List[str]:
    """
    Extract the top `max_keywords` longest words from the error string as search terms.
    """
    words = re.findall(r'\w+', error)
    keywords = [w for w in words if len(w) >= min_length]
    keywords.sort(key=len, reverse=True)
    return keywords[:max_keywords]

def find_code_matches(
    keywords: List[str],
    code_dir: Path,
    file_extensions: Optional[List[str]] = None
) -> Dict[Path, List[str]]:
    """
    Search for any of the keywords in code files under `code_dir`.
    Returns a mapping from file path to list of matching lines with line numbers.
    """
    if file_extensions is None:
        file_extensions = ['.py', '.cs', '.java', '.cpp', '.js', '.ts']

    matches: Dict[Path, List[str]] = defaultdict(list)
    for file in code_dir.rglob('*'):
        if file.suffix.lower() in file_extensions:
            try:
                with file.open(errors='ignore') as f:
                    for lineno, line in enumerate(f, start=1):
                        for kw in keywords:
                            if kw.lower() in line.lower():
                                matches[file].append(f"{lineno}: {line.strip()}")
                                break  # avoid duplicate matches on same line
            except Exception:
                continue
    return matches

def link_errors_to_code(
    errors: List[str],
    code_dir: Path
) -> Dict[str, Dict[Path, List[str]]]:
    """
    For each error message, extract keywords and search `code_dir` for matches.
    Returns a mapping from error message to a dict of file paths and their matching lines.
    """
    error_map: Dict[str, Dict[Path, List[str]]] = {}
    for err in errors:
        keywords = extract_keywords(err)
        matches = find_code_matches(keywords, code_dir)
        error_map[err] = matches
    return error_map
