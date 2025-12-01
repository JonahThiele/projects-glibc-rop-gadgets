import os
import re
from pathlib import Path
from unittest.mock import patch, MagicMock
from webscraping.ubuntu import generate_gadget_file


def test_generate_gadget_file_success(tmp_path):
    """
    Ensure gadget file is created, ropper is called correctly,
    and LOAD/INFO lines are removed using the given pattern.
    """

    name = "libc6_2.31-0ubuntu9_amd64.deb"
    libc_path = tmp_path / "libc.so.6"
    libc_path.write_text("dummy")

    gadgets_dir = tmp_path / "gadgets"
    pattern = re.compile(r"\[LOAD\]|\[INFO\]", re.IGNORECASE)

    # Mock subprocess.run, does NOT call ropper
    mock_proc = MagicMock()
    mock_proc.returncode = 0

    # The output ropper would "write"
    ropper_output = (
        "gadget1\n"
        "[LOAD] skip this\n"
        "gadget2\n"
        "[INFO] skip this too\n"
        "gadget3\n"
    )

    def fake_run(cmd, stdout, stderr, check, text):
        stdout.write(ropper_output)
        return mock_proc

    with patch("subprocess.run", side_effect=fake_run):
        created_path = generate_gadget_file(
            name=name,
            libc_path=str(libc_path),
            gadgets_dir=str(gadgets_dir),
            arch="amd64",       # ignored by function (parsed from filename)
            pattern=pattern,
        )

    # Check returned path is correct
    parts = name.split("_")
    version = parts[1].replace("-", "_")
    arch = parts[2].replace(".deb", "")
    expected_path = gadgets_dir / arch / f"glibc_{version}_{arch}.txt"

    assert created_path == str(expected_path)
    assert expected_path.exists()

    # LOAD/INFO lines should be removed
    filtered = expected_path.read_text().strip().splitlines()
    assert filtered == ["gadget1", "gadget2", "gadget3"]


def test_generate_gadget_file_calls_ropper_correctly(tmp_path):
    # Ensure the subprocess.run call uses the correct command and arguments.

    name = "libc6_2.40-1_i386.deb"
    libc_path = tmp_path / "libc.so.6"
    libc_path.write_text("x")

    gadgets_dir = tmp_path / "gadgets"
    pattern = re.compile(r"x")  # irrelevant

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock()
        mock_run.return_value.returncode = 0

        def fake_write(cmd, stdout, stderr, check, text):
            stdout.write("ok\n")
            return mock_run.return_value

        mock_run.side_effect = fake_write

        generate_gadget_file(name, str(libc_path), str(gadgets_dir), "ignored", pattern)

    mock_run.assert_called_once()

    cmd_used = mock_run.call_args.args[0]
    assert cmd_used == ["ropper", "--nocolor", "--file", str(libc_path)]

def test_generate_gadget_file_unknown_fields(tmp_path):
    """
    Triggers the fallback branch:
        raw_version = 'unknown'
        arch = 'unknown'
    by giving a filename with fewer than 3 parts.
    """
    name = "badname.deb"

    libc_path = tmp_path / "libc.so.6"
    libc_path.write_text("dummy")

    gadgets_dir = tmp_path / "gadgets"
    pattern = re.compile(r"\[LOAD\]", re.IGNORECASE)

    # Mock subprocess.run so no ropper actually runs
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock()
        mock_run.return_value.returncode = 0

        def fake_run(cmd, stdout, stderr, check, text):
            stdout.write("valid_line\n[LOAD] bad\n")
            return mock_run.return_value

        mock_run.side_effect = fake_run

        created_path = generate_gadget_file(
            name=name,
            libc_path=str(libc_path),
            gadgets_dir=str(gadgets_dir),
            arch="ignored",     # overridden by fallback logic
            pattern=pattern,
        )

    # Expected fallback path
    expected = gadgets_dir / "unknown" / "glibc_unknown_unknown.txt"
    assert created_path == str(expected)
    assert expected.exists()

    # verify fallback values hit
    assert "glibc_unknown_unknown.txt" in created_path

    # verify filtering still happened
    lines = expected.read_text().splitlines()
    assert lines == ["valid_line"]
