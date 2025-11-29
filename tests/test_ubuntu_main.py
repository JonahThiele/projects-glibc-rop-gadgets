import os
import shutil
import pytest
from unittest.mock import patch

# Helper fake stuffs
class FakeLink:
    def __init__(self, text):
        self.text = text
        self.next_siblings = []  # simulate no siblings

    def get(self, key):
        return "href"

class FakeSoup:
    def __init__(self, links):
        self._links = links

    def find_all(self, tag, href):
        return self._links


# Test 1 - skips download process for duplicates
def test_main_skips_existing(monkeypatch, capsys):
    # Fake page with a single valid libc link
    fake_link = FakeLink("libc6_2.31-0ubuntu9_amd64.deb")
    fake_soup = FakeSoup([fake_link])

    # Mock setup_environment → returns fake soup
    monkeypatch.setattr("webscraping.ubuntu.setup_environment",
                        lambda *a, **k: fake_soup)

    # Pretend gadget file already exists
    monkeypatch.setattr("os.path.exists", lambda x: True)

    # Ensure download / extract / generate are NOT called
    monkeypatch.setattr("webscraping.ubuntu.download_deb",
                        lambda *a, **k: pytest.fail("download_deb should NOT be called"))
    monkeypatch.setattr("webscraping.ubuntu.extract_libc",
                        lambda *a, **k: pytest.fail("extract_libc should NOT be called"))
    monkeypatch.setattr("webscraping.ubuntu.generate_gadget_file",
                        lambda *a, **k: pytest.fail("generate_gadget_file should NOT be called"))

    monkeypatch.setattr("shutil.rmtree", lambda *a: None)

    from webscraping.ubuntu import main
    main()

    output = capsys.readouterr().out
    assert "Already exists — skipping download" in output


# Test 2 - download, extraction, and file generation when file missing
def test_main_downloads_if_missing(monkeypatch):
    calls = {"download": False, "extract": False, "generate": False}

    fake_link = FakeLink("libc6_2.31-0ubuntu9_amd64.deb")
    fake_soup = FakeSoup([fake_link])

    monkeypatch.setattr("webscraping.ubuntu.setup_environment",
                        lambda *a, **k: fake_soup)

    # Pretend gadget file does not exist
    monkeypatch.setattr("os.path.exists", lambda x: False)

    # Track calls to each function
    monkeypatch.setattr("webscraping.ubuntu.download_deb",
                        lambda *a, **k: calls.__setitem__("download", True) or "/tmp/fake.deb")
    monkeypatch.setattr("webscraping.ubuntu.extract_libc",
                        lambda *a, **k: calls.__setitem__("extract", True) or "/tmp/libc.so.6")
    monkeypatch.setattr("webscraping.ubuntu.generate_gadget_file",
                        lambda *a, **k: calls.__setitem__("generate", True) or "/tmp/output.txt")

    monkeypatch.setattr("shutil.rmtree", lambda *a: None)

    from webscraping.ubuntu import main
    main()

    assert calls["download"]
    assert calls["extract"]
    assert calls["generate"]


# Test 3 - Removing directories
def test_main_removes_download_dir(monkeypatch):
    removed = {"flag": False}

    fake_soup = FakeSoup([])

    monkeypatch.setattr("webscraping.ubuntu.setup_environment",
                        lambda *a, **k: fake_soup)

    def fake_rmtree(path):
        removed["flag"] = True

    monkeypatch.setattr("shutil.rmtree", fake_rmtree)
    monkeypatch.setattr("os.path.exists", lambda x: False)

    from webscraping.ubuntu import main
    main()

    assert removed["flag"], "main() did not call shutil.rmtree()"


#Test 4 - cleanup error handling
def test_main_cleanup_error(monkeypatch, capsys):
    fake_soup = FakeSoup([])

    monkeypatch.setattr("webscraping.ubuntu.setup_environment",
                        lambda *a, **k: fake_soup)

    def fake_rmtree(path):
        raise OSError("permission denied")

    monkeypatch.setattr("shutil.rmtree", fake_rmtree)

    from webscraping.ubuntu import main
    main()

    output = capsys.readouterr().out
    assert "Error removing" in output