#!/usr/bin/env python3
"""
Simple test script for fedora.py
"""

import sys
import os
import unittest
import pytest
from unittest.mock import patch, Mock

# Add parent directory to path to import the script
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from webscraping import fedora as script


def test_create_libc_filename():
    """Test the create_libc_filename function"""
    print("Testing create_libc_filename...")
    
    test_cases = [
        ("glibc-2.34-10.fc35.x86_64.rpm", "libc-2.34.so"),
        ("glibc-2.35-5.fc36.i686.rpm", "libc-2.35.so"),
    ]
    
    for rpm_file, expected in test_cases:
        result = script.create_libc_filename(rpm_file)
        print(f"  {rpm_file} -> {result} (expected: {expected})")
        assert result == expected, f"Expected {expected}, got {result}"
    
    print("  ✓ create_libc_filename tests passed")

def test_libc_paths():
    """Test that LIBC_PATHS is properly defined"""
    print("Testing LIBC_PATHS...")
    
    assert hasattr(script, 'LIBC_PATHS'), "LIBC_PATHS not defined"
    assert isinstance(script.LIBC_PATHS, list), "LIBC_PATHS should be a list"
    assert len(script.LIBC_PATHS) > 0, "LIBC_PATHS should not be empty"
    
    for path in script.LIBC_PATHS:
        assert isinstance(path, str), f"Path {path} should be a string"
        assert 'libc.so.6' in path, f"Path {path} should contain libc.so.6"
    
    print("  ✓ LIBC_PATHS tests passed")

@patch('webscraping.fedora.requests.get')
def test_mock_scraping(mock_get):
    """Test scraping with mocked requests"""
    print("Testing scraping with mocked requests...")
    
    # Mock HTML response
    mock_html = """
    <html>
    <body>
        <a href="buildinfo?buildID=12345">glibc-2.34-10.fc35</a>
        <a href="buildinfo?buildID=67890">glibc-2.35-5.fc36</a>
    </body>
    </html>
    """
    
    mock_response = Mock()
    mock_response.content = mock_html.encode('utf-8')
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response
    
    version_dict = {}
    result = script.scrape_glibc_versions_from_page("http://test.url", version_dict)
    
    assert result == True, "Scraping should return True when glibc found"
    assert len(version_dict) == 2, f"Should find 2 versions, found {len(version_dict)}"
    
    print("  ✓ Mock scraping tests passed")

@patch('webscraping.fedora.requests.get')
def test_extract_rpm_urls_from_buildinfo(mock_get):
    """Test extracting RPM links from a mock buildinfo page"""
    print("Testing extract_rpm_urls_from_buildinfo...")
    
    mock_html = """
    <html>
    <body>
        <a href="https://koji.fedoraproject.org/packages/glibc/2.34/10/x86_64/glibc-2.34-10.fc35.x86_64.rpm">glibc-x86_64.rpm</a>
        
        <a href="https://koji.fedoraproject.org/packages/glibc/2.34/10/i686/glibc-2.34-10.fc35.i686.rpm">glibc-i686.rpm</a>
        
        <a href="https://koji.fedoraproject.org/packages/glibc/2.34/10/x86_64/glibc-debuginfo-2.34-10.fc35.x86_64.rpm">glibc-debuginfo.rpm</a>
    </body>
    </html>
    """
    
    mock_response = Mock()
    mock_response.content = mock_html.encode('utf-8')
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response
    
    urls = script.extract_rpm_urls_from_buildinfo("http://fake.url/buildinfo")
    
    assert 'x86_64' in urls, "Should have found x86_64 architecture"
    assert 'i686' in urls, "Should have found i686 architecture"
    assert "x86_64" in urls['x86_64']
    assert "debuginfo" not in str(urls.values()), "Should exclude debuginfo packages"
    
    print("  ✓ extract_rpm_urls_from_buildinfo passed")

@patch('webscraping.fedora.scrape_glibc_versions_from_page')
@patch('webscraping.fedora.requests.get')
def test_get_glibc_versions_pagination(mock_get, mock_scrape):
    """Test that the scraper handles pagination correctly"""
    print("Testing get_glibc_versions_all_pages pagination...")
    mock_scrape.side_effect = [True, True, False]
    
    page1_html = """
    <html><body>
        <a href="?buildStart=50">Next &gt;&gt;</a>
    </body></html>
    """
    
    page2_html = """
    <html><body>
        <span>No more results</span>
    </body></html>
    """
    
    mock_resp1 = Mock()
    mock_resp1.content = page1_html.encode('utf-8')
    mock_resp1.raise_for_status.return_value = None
    
    mock_resp2 = Mock()
    mock_resp2.content = page2_html.encode('utf-8')
    mock_resp2.raise_for_status.return_value = None

    mock_get.side_effect = [mock_resp1, mock_resp2]

    script.get_glibc_versions_all_pages(quiet=True)
    
    assert mock_get.call_count == 2, f"Expected 2 page loads, got {mock_get.call_count}"
    assert mock_scrape.call_count == 3, f"Expected 3 scrape attempts, got {mock_scrape.call_count}"
    
    print("  ✓ get_glibc_versions_all_pages pagination passed")

def test_copy_binary_integration():
    """Test file copying functionality"""
    print("Testing copy_binary function...")
    
    import tempfile
    import shutil
    
    # Create temporary directory
    test_dir = tempfile.mkdtemp()
    
    try:
        # Create source file
        source_path = os.path.join(test_dir, "test_source.bin")
        dest_path = os.path.join(test_dir, "subdir", "test_dest.bin")
        
        with open(source_path, 'w') as f:
            f.write("test content")
        
        # Test successful copy
        result = script.copy_binary(source_path, dest_path)
        assert result == True, "Copy should succeed"
        assert os.path.exists(dest_path), "Destination file should exist"
        
        # Test non-existent source
        result = script.copy_binary("/nonexistent/file", dest_path)
        assert result == False, "Copy should fail with non-existent source"
        
        print("  ✓ copy_binary tests passed")
        
    finally:
        # Clean up
        shutil.rmtree(test_dir)

@patch('builtins.open', new_callable=unittest.mock.mock_open)
@patch('webscraping.fedora.requests.get')
@patch('webscraping.fedora.fetch_rpm_urls_all_versions') # Mock the URL fetcher helper
def test_download_rpms(mock_fetch_urls, mock_get, mock_file):
    """Test the file download loop"""
    print("Testing download_rpms_all_version...")
    
    mock_fetch_urls.return_value = ["http://example.com/test_package.rpm"]

    mock_response = Mock()
    mock_response.iter_content.return_value = [b'chunk1', b'chunk2']
    mock_response.raise_for_status.return_value = None
    mock_get.return_value.__enter__.return_value = mock_response 

    script.download_rpms_all_version(quiet=True)

    args, _ = mock_file.call_args
    assert "test_package.rpm" in args[0]
    
    print("  ✓ download_rpms_all_version passed")

@patch('webscraping.fedora.subprocess.Popen')
@patch('webscraping.fedora.os.path.exists')
def test_extract_with_rpm2cpio(mock_exists, mock_popen):
    """Test the extraction pipeline"""
    print("Testing extract_with_rpm2cpio...")
    
    mock_exists.side_effect = lambda x: "libc.so.6" in x
    
    process_mock = Mock()
    process_mock.stdout.close = Mock()
    process_mock.communicate.return_value = (b"output", b"error")
    process_mock.returncode = 0
    
    mock_popen.return_value = process_mock
    
    result = script.extract_with_rpm2cpio("glibc-2.34-10.rpm", "output_dir")
    
    assert result is not None
    assert "libc.so.6" in result
    assert mock_popen.call_count == 2 # Once for rpm2cpio, once for cpio
    
    print("  ✓ extract_with_rpm2cpio passed")

@patch('webscraping.fedora.subprocess.run')
@patch('webscraping.fedora.extract_all_rpms')
@patch('webscraping.fedora.shutil.rmtree') # Prevent deleting real folders
@patch('builtins.open', new_callable=unittest.mock.mock_open, read_data="[INFO] Junk\nROP_GADGET_HERE\n[LOAD] More Junk")
def test_create_rop_gadgets(mock_file, mock_rmtree, mock_extract, mock_run):
    """Test ROP gadget creation and cleanup"""
    print("Testing create_rop_gadgets...")
    
    mock_extract.return_value = ["glibc-2.34-10_fc35_x86_64_libc.so.6"]
    
    script.create_rop_gadgets(quiet=True)
    
    args, _ = mock_run.call_args
    assert args[0][0] == "ropper"
    
    assert mock_file.call_count >= 2
    
    print("  ✓ create_rop_gadgets passed")