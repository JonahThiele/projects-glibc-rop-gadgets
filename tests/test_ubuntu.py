import pytest
import requests
from bs4 import BeautifulSoup
from webscraping import ubuntu as ub
from datetime import datetime
import re

#using a fixture for the ubuntu scripts so that we can use the same environment
#across all tests
@pytest.fixture
def mocks(monkeypatch):
    calls=[]
    def mock_makedirs(path, exist_ok=False):
        cur_call = {}
        cur_call['path'] = path
        cur_call['exist_ok'] = exist_ok
        calls.append(cur_call)

    class mockResponse:
        def __init__(self, text):
            self.text = text

    def mock_request(path):
        calls.append({'url': path})
        return mockResponse("<html><p>This is HTML</p></html>")
    

    monkeypatch.setattr("os.makedirs", mock_makedirs)
    monkeypatch.setattr(requests, "get", mock_request)
    return calls

#tests for get_file_date function 
#can't get the exception to get hit
def test_get_file_date_should_handle_exceptions():
    #arrange
    class mockSession:
        def head(self, *args, **kwargs):
            raise RuntimeError("network failure")
        
    link = type("L", (), {"next_siblings": []})()
    file_url = "file_url"
    # act
    result = ub.get_file_date(link, file_url, max_sibling_steps=4, session=mockSession())
    # assert
    assert result == None
    
def test_get_file_date_should_handle_datetime_strptime_incorrect_format():
    # arrange
    class mockedLink:
        def __init__(self):
            self.next_siblings = ['32-Jan-2023']

    link = mockedLink()
    file_url = "file_url"
    # act
    result = ub.get_file_date(link, file_url, max_sibling_steps=4, session=None)
    # assert
    assert result == None
    
def test_get_file_data_fails_to_get_head():
    # second rount of testing
    link = type("L", (), {"next_siblings": []})()
    file_url = "file_url"
    # act
    result = ub.get_file_date(link, file_url, max_sibling_steps=4, session=None)
    # assert
    assert result == None

def test_get_file_data_if_sib_is_None():
    # second rount of testing
    link = type("L", (), {"next_siblings": [None]})()
    file_url = "file_url"
    # act
    result = ub.get_file_date(link, file_url, max_sibling_steps=4, session=None)
    # assert
    assert result == None

def test_get_file_data_if_sibling_greater_than_step():
    # second rount of testing
    link = type("L", (), {"next_siblings": [None, None, 'link']})()
    file_url = "file_url"
    # act
    result = ub.get_file_date(link, file_url, max_sibling_steps=1, session=None)
    # assert
    assert result == None 

#tests for setup environment function
def test_setup_environment_should_generate_folders(mocks):
    #arrange
    #inputs for function, they don't have to be the exact arguments
    #that we use in the program, but they should be reasonable arguments
    url = 'https://archive.ubuntu.com/ubuntu/pool/main/g/glibc/'
    downloads = '../GlibcDownloads'
    gadgets = '../Gadgets/Ubuntu'
    #we shouldn't need to make sure that the code of the OS is working,
    #ie that the folder is being created on disk just that our paths and inputs makes sense
    #act
    ub.setup_environment(url, downloads, gadgets)
    #assert
    paths = [call['path'] for call in mocks if 'path' in call]
    
    #two folders created
    assert len(paths) == 2

    assert downloads in paths
    assert gadgets in paths

    assert all([call['exist_ok'] for call in mocks if 'exist_okay' in call])

def test_setup_environment_should_get_request(mocks):
    # arrange
    url = 'https://archive.ubuntu.com/ubuntu/pool/main/g/glibc/'
    downloads = '../GlibcDownloads'
    gadgets = '../Gadgets/Ubuntu'

    # act
    ub.setup_environment(url, downloads, gadgets)

    # assert
    called_url = [call['url'] for call in mocks if 'url' in call]
    assert called_url[0] == url
    #don't know whether to add the code that checks if it's valid html
    #that is returned or not

def test_setup_environment_should_parse_html():
    # arrange
    url = 'https://archive.ubuntu.com/ubuntu/pool/main/g/glibc/'
    downloads = '../GlibcDownloads'
    gadgets = '../Gadgets/Ubuntu'

    # act
    result = ub.setup_environment(url, downloads, gadgets)
    
    # assert
    #just make sure the the soup object is not null
    assert result != None
    assert isinstance(result, BeautifulSoup)

#tests for should_process_file function
def test_should_not_process_file_if_not_ends_with_deb():
    # arrange
    name = 'libc6_2.23-0ubuntu3_amd64.rpm'
    skip = re.compile(r"(-dev|-dbg|-bin|-doc|-locale|-prof|_all\.deb$)")
    cutoff_date =  datetime(2025, 1, 1).date()
    link = 'https://archive.ubuntu.com/ubuntu/pool/main/g/glibc/libc6_2.23-0ubuntu3_amd64.rpm'
    url_prefix = "https://archive.ubuntu.com/ubuntu/pool/main/g/glibc/"
    session = requests.Session()
    # act
    result = ub.should_process_file(name, skip, cutoff_date, link, url_prefix, session)
    # assert 
    assert result == (False, None)

def test_should_not_process_file_if_download_contains_skip():
    # arrange
    name = 'glibc-doc_2.23-0ubuntu3_all.deb'
    skip = re.compile(r"(-dev|-dbg|-bin|-doc|-locale|-prof|_all\.deb$)")
    cutoff_date =  datetime(2025, 1, 1).date()
    link = 'https://archive.ubuntu.com/ubuntu/pool/main/g/glibc/glibc-doc_2.23-0ubuntu3_all.deb'
    url_prefix = "https://archive.ubuntu.com/ubuntu/pool/main/g/glibc/"
    session = requests.Session()

    # act
    result = ub.should_process_file(name, skip, cutoff_date, link, url_prefix, session)

    # assert
    assert result == (False, None)

def test_should_not_process_file_if_file_date_early_than_cutoff(monkeypatch):
    # arrange
    name = 'libc6_2.23-0ubuntu3_amd64.deb'
    skip = re.compile(r"(-dev|-dbg|-bin|-doc|-locale|-prof|_all\.deb$)")
    cutoff_date =  datetime(2020, 1, 1).date()
    link = 'https://archive.ubuntu.com/ubuntu/pool/main/g/glibc/libc6_2.23-0ubuntu3_amd64.deb'
    url_prefix = "https://archive.ubuntu.com/ubuntu/pool/main/g/glibc/"
    session = requests.Session()

    def mock_get_file_date(*args, **kwargs):
        return datetime(2019, 1, 1).date()

    monkeypatch.setattr(ub, "get_file_date", mock_get_file_date)

    # act
    result = ub.should_process_file(name, skip, cutoff_date, link, url_prefix, session)

    # assert
    assert result == (False, datetime(2019, 1, 1).date())

def test_should_not_process_file_if_file_date_is_none(monkeypatch):
    # arrange
    name = 'libc6_2.23-0ubuntu3_amd64.deb'
    skip = re.compile(r"(-dev|-dbg|-bin|-doc|-locale|-prof|_all\.deb$)")
    cutoff_date =  datetime(2025, 1, 1).date()
    link = 'https://archive.ubuntu.com/ubuntu/pool/main/g/glibc/libc6_2.23-0ubuntu3_amd64.deb'
    url_prefix = "https://archive.ubuntu.com/ubuntu/pool/main/g/glibc/"
    session = requests.Session()

    def mock_get_file_date(*args, **kwargs):
        return None

    monkeypatch.setattr(ub, "get_file_date", mock_get_file_date)

    
    # act
    result = ub.should_process_file(name, skip, cutoff_date, link, url_prefix, session)

    # assert
    assert result == (True, None)

def test_should_not_process_file_if_file_is_multi_arch(monkeypatch):
    # arrange
    name = 'libc6-x32_2.35-0ubuntu3.12_i386.deb'
    skip = re.compile(r"(-dev|-dbg|-bin|-doc|-locale|-prof|_all\.deb$)")
    cutoff_date =  datetime(2025, 1, 1).date()
    link = 'https://archive.ubuntu.com/ubuntu/pool/main/g/glibc/multiarch-support_2.23-0ubuntu3_amd64.deb'
    url_prefix = "https://archive.ubuntu.com/ubuntu/pool/main/g/glibc/"
    session = requests.Session()

    def mock_get_file_date(*args, **kwargs):
        return datetime(2025, 1, 1).date()

    monkeypatch.setattr(ub, "get_file_date", mock_get_file_date)

    # act
    result = ub.should_process_file(name, skip, cutoff_date, link, url_prefix, session)

    # assert
    assert result == (False, datetime(2025, 1, 1).date())
