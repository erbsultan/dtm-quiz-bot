import argparse

import pytest

from scripts.extract_pdf_pages import parse_page_range


def test_parse_page_range_accepts_range():
    assert parse_page_range("142-145") == (142, 145)


def test_parse_page_range_accepts_single_page():
    assert parse_page_range("142") == (142, 142)


def test_parse_page_range_rejects_reversed_range():
    with pytest.raises(argparse.ArgumentTypeError):
        parse_page_range("145-142")
