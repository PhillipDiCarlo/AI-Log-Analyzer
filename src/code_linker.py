import re
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

def extract_keywords(error: str, min_length: int = 3, max_keywords: int = 3) -> List[str]:
    """
    Extract the top `max_keywords` longest words from the error string as search terms.
    """
    # Tokenize into alphanumeric words
    words = re.findall(r"\w+", error)
    # Filter out short words
    keywords = [w for w in words if len(w) >= min_length]
    # Sort descending by length
    keywords.sort(key=len, reverse=True)
    # Return only the top N
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
        if not file.is_file() or file.suffix.lower() not in file_extensions:
            continue
        try:
            with file.open(errors='ignore') as f:
                for lineno, line in enumerate(f, start=1):
                    lower = line.lower()
                    for kw in keywords:
                        if kw.lower() in lower:
                            matches[file].append(f"{lineno}: {line.strip()}")
                            break
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
        kws = extract_keywords(err)            # ['function', 'Error', 'bar']
        matches = find_code_matches(kws, code_dir)
        error_map[err] = matches
    return error_map
