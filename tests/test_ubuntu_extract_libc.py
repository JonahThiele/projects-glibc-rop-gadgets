import pytest
from pathlib import Path
from unittest.mock import patch
from webscraping.ubuntu import extract_libc

# Mock os.walk to simulate extracted files
def fake_os_walk_with_libc(dir_path):
    dir_path = Path(dir_path)
    return [
        (str(dir_path / "lib"), [], ["libc.so.6"]),
    ]

def fake_os_walk_no_libc(dir_path):
    dir_path = Path(dir_path)
    return [
        (str(dir_path / "lib"), [], ["otherfile.so"]),
    ]

def test_extract_libc_success(tmp_path):
    fake_deb = tmp_path / "package.deb"

    # Patch subprocess.run to skip real debx unpack
    # Patch os.walk to simulate a directory containing libc.so.6
    with patch("subprocess.run") as mock_run, \
         patch("os.walk", side_effect=fake_os_walk_with_libc):
        extracted = extract_libc(fake_deb)

    # Function returns a string path
    assert extracted != "", "Expected a non-empty path for libc.so.6"
    assert "libc.so.6" in extracted, f"Expected libc.so.6 in {extracted}"

def test_extract_libc_missing(tmp_path):
    fake_deb = tmp_path / "package.deb"
    # Same patch as before
    with patch("subprocess.run") as mock_run, \
         patch("os.walk", side_effect=fake_os_walk_no_libc):
        extracted = extract_libc(fake_deb)

    # Function returns empty string when libc is not found
    assert extracted == "" or extracted is None, f"Expected empty or None, got {extracted}"
