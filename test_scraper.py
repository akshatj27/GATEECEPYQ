import pytest
from unittest.mock import patch, MagicMock
import sys

# Mocking external dependencies before importing GATEScraper
sys.modules['requests'] = MagicMock()
sys.modules['bs4'] = MagicMock()

from scraper import GATEScraper

def test_init_defaults():
    with patch('os.path.exists', return_value=True):
        scraper = GATEScraper()
        assert scraper.branch == 'ec'
        assert scraper.output_dir == "gate_questions"
        assert scraper.debug is False
        assert scraper.max_threads == 5
        assert scraper.base_url == "https://practicepaper.in/gate-ec/gate-ec-year-wise-questions"

def test_init_custom_values():
    with patch('os.path.exists', return_value=True):
        scraper = GATEScraper(branch='ee', output_dir="custom_out", debug=True, max_threads=10)
        assert scraper.branch == 'ee'
        assert scraper.output_dir == "custom_out"
        assert scraper.debug is True
        assert scraper.max_threads == 10
        assert scraper.base_url == "https://practicepaper.in/gate-ee/gate-ee-year-wise-questions"

def test_init_branch_normalization():
    with patch('os.path.exists', return_value=True):
        scraper = GATEScraper(branch='CS')
        assert scraper.branch == 'cs'
        assert scraper.base_url == "https://practicepaper.in/gate-cs/gate-cs-year-wise-questions"

@patch('os.makedirs')
@patch('os.path.exists')
def test_init_creates_dir_if_not_exists(mock_exists, mock_makedirs):
    mock_exists.return_value = False
    scraper = GATEScraper(output_dir="new_dir")
    mock_exists.assert_called_with("new_dir")
    mock_makedirs.assert_called_with("new_dir")

@patch('os.makedirs')
@patch('os.path.exists')
def test_init_does_not_create_dir_if_exists(mock_exists, mock_makedirs):
    mock_exists.return_value = True
    scraper = GATEScraper(output_dir="existing_dir")
    mock_exists.assert_called_with("existing_dir")
    mock_makedirs.assert_not_called()

def test_init_headers():
    with patch('os.path.exists', return_value=True):
        scraper = GATEScraper()
        assert "User-Agent" in scraper.headers
        assert "Mozilla/5.0" in scraper.headers["User-Agent"]
