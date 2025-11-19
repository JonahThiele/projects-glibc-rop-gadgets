from bs4 import BeautifulSoup
import requests
import subprocess
import re
import os
import shutil
from datetime import datetime


# place near your imports
from datetime import datetime
from email.utils import parsedate_to_datetime

def get_file_date(link, file_url, max_sibling_steps=4, session=None):
    """
    Try to determine the file date for an archive link.
    1) Walk link.next_siblings (up to max_sibling_steps) and regex-search for 'DD-Mon-YYYY'
    2) If not found, send a HEAD request to file_url and try to parse Last-Modified header.
    Returns a datetime.date or None if unknown.
    """
    # 1) scan next_siblings
    sib_count = 0
    date_re = re.compile(r"(\d{2}-[A-Za-z]{3}-\d{4})")
    for sib in link.next_siblings:
        sib_count += 1
        if sib is None:
            continue
        text = str(sib).strip()
        if not text:
            # skip empty text nodes
            pass
        else:
            m = date_re.search(text)
            if m:
                try:
                    return datetime.strptime(m.group(1), "%d-%b-%Y").date()
                except Exception:
                    pass
        if sib_count >= max_sibling_steps:
            break

    # 2) fallback: HEAD request to get Last-Modified
    try:
        s = session or requests
        head = s.head(file_url, allow_redirects=True, timeout=10)
        if head.status_code == 200:
            lm = head.headers.get("Last-Modified")
            if lm:
                # parsedate_to_datetime handles RFC-822 dates used in HTTP headers
                try:
                    dt = parsedate_to_datetime(lm)
                    # convert to date (tz-aware => convert to UTC then date)
                    if dt.tzinfo is not None:
                        dt = dt.astimezone(tz=None)  # local zone; we only need date portion
                    return dt.date()
                except Exception:
                    pass
    except Exception:
        # network failure / timeout, we'll return None
        pass

    return None


url_prefix = "https://archive.ubuntu.com/ubuntu/pool/main/g/glibc/"

# Where I want things to download to, you can change to whatever you want
download_dir = '../GlibcDownloads'
gadgets_dir = '../Gadgets/Ubuntu'

#makes sure dir exists
os.makedirs(download_dir, exist_ok=True)
os.makedirs(gadgets_dir, exist_ok=True)


ubuntu_glibc = requests.get(url_prefix)
soup = BeautifulSoup(ubuntu_glibc.text, 'html.parser')

#Find only the packages we need, these formats
# libc6_<ver>_<arch>.deb
# libc6-i386_<ver>_amd64.deb
# libc6-amd64_<ver>_i386.deb
# libc6-x32_<ver>_amd64.deb

match = re.compile(
    r"^libc6(-[a-z0-9]+)?_[0-9].*_(amd64|amd64v3|i386|arm64|armhf|x32)\.deb$"
)

#regex for reducing file size
pattern = re.compile(r"\[LOAD\]|\[INFO\]", re.IGNORECASE)

#Skip over the stuff we dont need
skip = re.compile(r"(-dev|-dbg|-bin|-doc|-locale|-prof|_all\.deb$)")

count = 0
cutoff_date = datetime(2020, 1, 1).date()
session = requests.Session()  # reuse connection for HEADs

for link in soup.find_all("a", href=True):
    name = link.text.strip()
    if not name.endswith(".deb"):
        continue
    if skip.search(name):
        continue

    file_url = url_prefix + name    # build file_url

    # get file_date (tries siblings, then HEAD)
    file_date = get_file_date(link, file_url, max_sibling_steps=6, session=session)
    if file_date is not None:
        if file_date < cutoff_date:
            print(f"Skipping (too old {file_date}): {name}")
            continue
    else:
        # If date not found, download, can change to continue
        print(f"Warning: couldn't determine date for {name}; proceeding to download")

    if re.match(r"libc6-(amd64|i386|arm64|armhf|x32)_", name): # skip multi arch versions
        parts = name.split("_") # chunks the version name to see if 2 arch mentioned
        if len(parts) >= 3:
            prefix_arch = re.search(r"libc6-([^-_]+)", parts[0]).group(1)
            file_arch = parts[-1].replace(".deb", "")
            if prefix_arch != file_arch:
                print(f"Skipping (multiarch): {name}")
                continue

    if match.match(name): # Found a match, download
        # Determine architecture from filename
        arch = name.split("_")[-1].replace(".deb", "")
        arch_dir = os.path.join(gadgets_dir, arch)
        os.makedirs(arch_dir, exist_ok=True) #make subfolers for each arch

        gadget_path = os.path.join(gadgets_dir, name[:-4] + ".txt") # check subfolders for existing file
        if os.path.exists(gadget_path):
            print(f"Skipping (already exists): {name}")
            continue

        file_path = os.path.join(download_dir, name)
        print(f"Downloading: {name}")
        link_download = requests.get(url_prefix + name, stream=True)
        with open(file_path, mode="wb") as file:
            for chunk in link_download.iter_content(chunk_size=10 * 1024):
                file.write(chunk)
        count += 1

        # Unpack using the full path
        subprocess.run(["debx", "unpack", file_path])
        dir_path = file_path[:-4]

        #walk the files and find the libc.so.6
        libc_path = ""
        #check if folder contains data.tar.zst
        data_tar_zst_path = os.path.join(dir_path, "data.tar.zst")
        data_tar_path = os.path.join(dir_path, "data.tar")
        data_path = os.path.join(dir_path, "data")
        libc = "libc.so.6"

        if os.path.isfile(data_tar_zst_path):
            subprocess.run(['zstd', '-d', data_tar_zst_path, '-o', data_tar_path], check=True)
            subprocess.run(['tar', '-xf', data_tar_path, '-C', dir_path], check=True)
            for root, dirs, files in os.walk(os.path.join(dir_path)):
                if libc in files:
                    libc_path = os.path.join(root, libc)
        else:
            for root, dirs, files in os.walk(dir_path):
                if libc in files:
                    libc_path = os.path.join(root, libc)
                    break
        arch = name.split("_")[-1].replace(".deb", "")

        # Make a subfolder for that architecture
        arch_dir = os.path.join(gadgets_dir, arch)
        os.makedirs(arch_dir, exist_ok=True)


        # Make a subfolder for that architecture
        arch_dir = os.path.join(gadgets_dir, arch)
        os.makedirs(arch_dir, exist_ok=True)

        # Convert filename to new standardized format
        parts = name.split("_")
        if len(parts) >= 3:
            raw_version = parts[1]
            arch = parts[2].replace(".deb", "")
        else:
            raw_version = "unknown"
            arch = "unknown"

        version = raw_version.replace("-", "_")
        new_filename = f"glibc_{version}_{arch}.txt"
        gadget_path = os.path.join(arch_dir, new_filename)

        with open(gadget_path, "w") as out:
            subprocess.run(
                ["ropper", "--nocolor", "--file", libc_path],
                stdout=out,
                stderr=subprocess.STDOUT,
                check=True,
                text=True)
        
        # remove first LOAD and INFO lines by copying the file into memory
        # probably a more efficient way of doing this but this should work
        with open(gadget_path, "r") as f:
            lines = f.readlines()
        with open(gadget_path, "w") as f:
            for line in lines:
                if not pattern.search(line):
                    f.write(line)

#delete GlibcDownloads folder and contents
try:
    shutil.rmtree(download_dir)
    print(f"Removed download directory: {download_dir}")
except OSError as e:
    print(f"Error removing {download_dir}: {e.strerror}")

print(f"\nDone — {count} files downloaded to {download_dir}")
