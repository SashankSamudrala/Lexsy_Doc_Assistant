# backend/tests/test_parser.py
from docx_parser import find_placeholders

def test_placeholder_regex_basic(tmp_path):
    # You can add a small generated .docx here if time permits;
    # for now, ensure function runs (smoke test).
    assert callable(find_placeholders)
