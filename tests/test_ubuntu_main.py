import os
import re
import shutil
import pytest
from unittest.mock import patch

class FakeLink:
    def __init__(self, text):
        self.text = text
        self.next_siblings = []

class FakeSoup:
    def __init__(self, links):
        self._links = links

    def find_all(self, tag, href):
        return self._links

# Test 1 — Skip existing gadget
def test_main_skips_existing(monkeypatch, capsys):
    fake_link = FakeLink("libc6_2.31-0ubuntu9_amd64.deb")
    fake_soup = FakeSoup([fake_link])

    monkeypatch.setattr("webscraping.ubuntu.setup_environment",
                        lambda *a, **k: fake_soup)

    # force main() to run the body
    monkeypatch.setattr("webscraping.ubuntu.should_process_file",
                        lambda *a, **k: (True, None))
    monkeypatch.setattr("webscraping.ubuntu.re", re)

    # gadget exists → should skip
    monkeypatch.setattr("os.path.exists", lambda x: True)

    monkeypatch.setattr("webscraping.ubuntu.download_deb",
                        lambda *a, **k: pytest.fail("download_deb should NOT be called"))
    monkeypatch.setattr("webscraping.ubuntu.extract_libc",
                        lambda *a, **k: pytest.fail("extract_libc should NOT be called"))
    monkeypatch.setattr("webscraping.ubuntu.generate_gadget_file",
                        lambda *a, **k: pytest.fail("generate_gadget_file should NOT be called"))

    monkeypatch.setattr("shutil.rmtree", lambda *a: None)

    from webscraping.ubuntu import main
    main()

    out = capsys.readouterr().out
    assert "Already exists — skipping download" in out

# Test 2 — Download/extract/generate
def test_main_downloads_if_missing(monkeypatch):
    calls = {"download": False, "extract": False, "generate": False}

    fake_link = FakeLink("libc6_2.31-0ubuntu9_amd64.deb")
    fake_soup = FakeSoup([fake_link])

    monkeypatch.setattr("webscraping.ubuntu.setup_environment",
                        lambda *a, **k: fake_soup)

    # allow processing
    monkeypatch.setattr("webscraping.ubuntu.should_process_file",
                        lambda *a, **k: (True, None))
    monkeypatch.setattr("webscraping.ubuntu.re", re)

    monkeypatch.setattr("os.path.exists", lambda x: False)

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



# Test 3 — Directory removal
def test_main_removes_download_dir(monkeypatch):
    removed = {"flag": False}

    fake_soup = FakeSoup([])

    monkeypatch.setattr("webscraping.ubuntu.setup_environment",
                        lambda *a, **k: fake_soup)

    # allow processing
    monkeypatch.setattr("webscraping.ubuntu.should_process_file",
                        lambda *a, **k: (True, None))
    monkeypatch.setattr("webscraping.ubuntu.re", re)

    def fake_rmtree(path):
        removed["flag"] = True

    monkeypatch.setattr("shutil.rmtree", fake_rmtree)
    monkeypatch.setattr("os.path.exists", lambda x: False)

    from webscraping.ubuntu import main
    main()

    assert removed["flag"]


# Test 4 — Cleanup error handling
def test_main_cleanup_error(monkeypatch, capsys):
    fake_soup = FakeSoup([])

    monkeypatch.setattr("webscraping.ubuntu.setup_environment",
                        lambda *a, **k: fake_soup)

    # allow processing
    monkeypatch.setattr("webscraping.ubuntu.should_process_file",
                        lambda *a, **k: (True, None))
    monkeypatch.setattr("webscraping.ubuntu.re", re)

    def fake_rmtree(path):
        raise OSError("permission denied")

    monkeypatch.setattr("shutil.rmtree", fake_rmtree)

    from webscraping.ubuntu import main
    main()

    output = capsys.readouterr().out
    assert "Error removing" in output

#For line 188
def test_main_skips_when_should_process_file_false(monkeypatch, capsys):
    fake_link = FakeLink("libc6_2.31-0ubuntu9_amd64.deb")
    fake_soup = FakeSoup([fake_link])
    monkeypatch.setattr("webscraping.ubuntu.setup_environment", lambda *a, **k: fake_soup)
    
    # This triggers line 188
    monkeypatch.setattr("webscraping.ubuntu.should_process_file", lambda *a, **k: (False, None))
    
    # ensure regex still works
    monkeypatch.setattr("webscraping.ubuntu.re", re)
    
    # patch rmtree to avoid cleanup
    monkeypatch.setattr("shutil.rmtree", lambda *a: None)
    
    from webscraping.ubuntu import main
    main()
    
    out = capsys.readouterr().out
    # Should NOT attempt download
    assert "Already exists" not in out

#For line 191
def test_main_skips_nonmatching_filename(monkeypatch, capsys):
    fake_link = FakeLink("randomfile.txt")  # doesn't match match regex
    fake_soup = FakeSoup([fake_link])
    monkeypatch.setattr("webscraping.ubuntu.setup_environment", lambda *a, **k: fake_soup)
    
    # should_process_file returns True, so line 191 is reached
    monkeypatch.setattr("webscraping.ubuntu.should_process_file", lambda *a, **k: (True, None))
    
    monkeypatch.setattr("webscraping.ubuntu.re", re)
    monkeypatch.setattr("shutil.rmtree", lambda *a: None)
    
    from webscraping.ubuntu import main
    main()
    
    out = capsys.readouterr().out
    # Should NOT attempt download
    assert "Already exists" not in out