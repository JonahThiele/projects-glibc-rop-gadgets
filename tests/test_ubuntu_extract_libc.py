import os
from pathlib import Path
from unittest.mock import patch, call
import pytest
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
    # prepare a fake .deb path
    fake_deb = tmp_path / "package.deb"
    fake_deb.write_text("dummy")

    # The function builds dir_path by stripping .deb
    unpack_dir = Path(str(fake_deb)[:-4])
    unpack_dir.mkdir(parents=True, exist_ok=True)

    # create a data.tar.zst file so the code takes the zstd/tar branch
    zst_path = unpack_dir / "data.tar.zst"
    zst_path.write_text("fake-zst")

    # Patch os.walk to simulate a directory containing libc.so.6
    with patch("os.walk", side_effect=fake_os_walk_with_libc):
        with patch("subprocess.run") as mock_run:
            extracted = extract_libc(fake_deb)

            # Function should return a path containing libc.so.6 (string in current impl)
            assert extracted != "" and "libc.so.6" in str(extracted)

            # assert subprocess.run was called for zstd and tar.
            # Order matters: first call is debx unpack (the first call in function),
            # subsequent calls are zstd and tar.
            calls = mock_run.call_args_list
            zstd_called = any(
                (isinstance(c.args[0], (list, tuple)) and c.args[0][0] == "zstd")
                or (isinstance(c.args[0], str) and "zstd" in c.args[0])
                for c in calls
            )
            tar_called = any(
                (isinstance(c.args[0], (list, tuple)) and c.args[0][0] == "tar")
                or (isinstance(c.args[0], str) and "tar" in c.args[0])
                for c in calls
            )

            assert zstd_called, f"Expected zstd call in subprocess.run calls: {calls}"
            assert tar_called, f"Expected tar call in subprocess.run calls: {calls}"

def test_extract_libc_missing(tmp_path):
    fake_deb = tmp_path / "package.deb"
    fake_deb.write_text("dummy")

    # Same patch as before but simulate no libc found
    with patch("subprocess.run") as mock_run, \
         patch("os.walk", side_effect=fake_os_walk_no_libc):
        extracted = extract_libc(fake_deb)

    # Function returns empty string (or None) when libc is not found
    assert extracted == "" or extracted is None, f"Expected empty or None, got {extracted}"
