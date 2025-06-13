from pathlib import Path
import tempfile
from src.code_linker import extract_keywords, find_code_matches, link_errors_to_code

def test_extract_keywords():
    err = "Failed to update user profile endpoint"
    kws = extract_keywords(err, min_length=4, max_keywords=3)

    # We expect the three longest words, in descending-length order:
    #    endpoint (8), profile (7), Failed (6)
    expected = ["endpoint", "profile", "Failed"]
    assert kws == expected

def test_find_code_matches(tmp_path):
    # create a fake code file
    code = """
    def foo(): pass
    # TODO: add error handler
    """
    f = tmp_path/"test.py"
    f.write_text(code)
    keywords = ["error", "foo"]
    matches = find_code_matches(keywords, tmp_path)
    assert f in matches
    # ensure we got at least one snippet
    assert any("error" in line.lower() or "foo" in line for line in matches[f])

def test_link_errors_to_code(tmp_path):
    # fake code and error
    code = "def bar(): pass"
    (tmp_path/"a.py").write_text(code)
    errs = ["Error in bar function"]
    mapping = link_errors_to_code(errs, tmp_path)
    assert errs[0] in mapping
    assert (tmp_path/"a.py") in mapping[errs[0]]
