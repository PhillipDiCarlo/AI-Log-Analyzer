import re
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

# Folders to skip entirely
_SKIP_DIRS = {
    "venv", "__pycache__", ".pytest_cache", ".venv",
    ".git", ".github", "node_modules"
}

def extract_keywords(error: str, min_length: int = 3, max_keywords: int = 3) -> List[str]:
    words = re.findall(r"\w+", error)
    keywords = [w for w in words if len(w) >= min_length]
    keywords.sort(key=len, reverse=True)
    return keywords[:max_keywords]

def find_code_matches(
    keywords: List[str],
    code_dir: Path,
    file_extensions: Optional[List[str]] = None
) -> Dict[Path, List[str]]:
    """
    Search for any of the keywords in code files under `code_dir`,
    skipping unwanted directories. Returns a mapping from file path
    to list of matching lines with line numbers.
    """
    if file_extensions is None:
        file_extensions = ['.py', '.cs', '.java', '.cpp', '.js', '.ts']

    matches: Dict[Path, List[str]] = defaultdict(list)
    for file in code_dir.rglob('*'):
        if not file.is_file():
            continue

        # skip any file inside unwanted dirs
        rel = file.relative_to(code_dir).parts
        if any(p in _SKIP_DIRS or p.startswith('.') for p in rel):
            continue

        if file.suffix.lower() not in file_extensions:
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
    For each error message, extract keywords and search `code_dir` for matches,
    using find_code_matches() which already skips your unwanted folders.
    """
    error_map: Dict[str, Dict[Path, List[str]]] = {}
    for err in errors:
        kws = extract_keywords(err)
        matches = find_code_matches(kws, code_dir)
        error_map[err] = matches
    return error_map
