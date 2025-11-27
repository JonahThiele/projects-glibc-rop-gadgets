# Starter stuff for pytest - must pip install pytest first
# use file to import funcs from then write tests for them
# To run tests, go to root dir, then run "pytest -v"
    # will run all tests in folder

import os
from unittest.mock import Mock
from webscraping.ubuntu import download_deb

def test_download_deb(monkeypatch, tmp_path):
    fake_response = Mock()
    fake_response.iter_content = lambda chunk_size: [b"chunk1", b"chunk2"]

    # Capture URL used
    requested_urls = []

    def fake_get(url, stream=True):
        requested_urls.append(url)
        return fake_response

    monkeypatch.setattr("requests.get", fake_get)

    # Call function
    filename = "testfile.deb"
    url_prefix = "http://dummyurl.com/"
    download_dir = tmp_path

    output_path = download_deb(filename, url_prefix, download_dir)

    # 1. Correct file path is returned
    expected_path = os.path.join(download_dir, filename)
    assert output_path == expected_path

    # 2. File was created
    assert os.path.exists(output_path)

    # 3. File contains exactly the written chunks
    with open(output_path, "rb") as f:
        data = f.read()
    assert data == b"chunk1chunk2"

    # 4. download_deb hit the correct URL
    assert requested_urls == ["http://dummyurl.com/testfile.deb"]