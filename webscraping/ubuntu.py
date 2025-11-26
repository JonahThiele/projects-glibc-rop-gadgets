from bs4 import BeautifulSoup
import requests
import subprocess
import re
import os
import shutil
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
        if text:
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
                try:
                    dt = parsedate_to_datetime(lm)
                    if dt.tzinfo is not None:
                        dt = dt.astimezone(tz=None)
                    return dt.date()
                except Exception:
                    pass
    except Exception:
        pass

    return None

url_prefix = "https://archive.ubuntu.com/ubuntu/pool/main/g/glibc/"

def setup_environment(url_prefix, download_dir, gadgets_dir):
    os.makedirs(download_dir, exist_ok=True)
    os.makedirs(gadgets_dir, exist_ok=True)

    ubuntu_glibc = requests.get(url_prefix)
    soup = BeautifulSoup(ubuntu_glibc.text, 'html.parser')
    return soup

def should_process_file(name, skip, cutoff_date, link, url_prefix, session):
    if not name.endswith(".deb"):
        return False, None

    if skip.search(name):
        return False, None

    file_url = url_prefix + name
    file_date = get_file_date(link, file_url, max_sibling_steps=6, session=session)

    if file_date is not None and file_date < cutoff_date:
        print(f"Skipping (too old {file_date}): {name}")
        return False, file_date

    if file_date is None:
        print(f"Warning: couldn't determine date for {name}; proceeding to download")

    # Skip incorrectly-matched multiarch files
    if re.match(r"libc6-(amd64|i386|arm64|armhf|x32)_", name):
        parts = name.split("_")
        if len(parts) >= 3:
            prefix_arch = re.search(r"libc6-([^-_]+)", parts[0]).group(1)
            file_arch = parts[-1].replace(".deb", "")
            if prefix_arch != file_arch:
                print(f"Skipping (multiarch): {name}")
                return False, file_date

    return True, file_date

def download_deb(name, url_prefix, download_dir):
    file_path = os.path.join(download_dir, name)
    print(f"Downloading: {name}")
    link_download = requests.get(url_prefix + name, stream=True)

    with open(file_path, "wb") as f:
        for chunk in link_download.iter_content(chunk_size=10 * 1024):
            f.write(chunk)

    return file_path

def extract_libc(file_path):
    subprocess.run(["debx", "unpack", file_path])
    dir_path = file_path[:-4]

    libc = "libc.so.6"
    data_tar_zst_path = os.path.join(dir_path, "data.tar.zst")
    data_tar_path = os.path.join(dir_path, "data.tar")
    libc_path = ""

    if os.path.isfile(data_tar_zst_path):
        subprocess.run(['zstd', '-d', data_tar_zst_path, '-o', data_tar_path], check=True)
        subprocess.run(['tar', '-xf', data_tar_path, '-C', dir_path], check=True)

    # Search extracted tree
    for root, dirs, files in os.walk(dir_path):
        if libc in files:
            libc_path = os.path.join(root, libc)
            break

    return libc_path

def generate_gadget_file(name, libc_path, gadgets_dir, arch, pattern):
    parts = name.split("_")
    if len(parts) >= 3:
        raw_version = parts[1]
        arch = parts[2].replace(".deb", "")
    else:
        raw_version = "unknown"
        arch = "unknown"

    version = raw_version.replace("-", "_")
    new_filename = f"glibc_{version}_{arch}.txt"

    arch_dir = os.path.join(gadgets_dir, arch)
    os.makedirs(arch_dir, exist_ok=True)

    gadget_path = os.path.join(arch_dir, new_filename)

    # Run ropper
    with open(gadget_path, "w") as out:
        subprocess.run(
            ["ropper", "--nocolor", "--file", libc_path],
            stdout=out,
            stderr=subprocess.STDOUT,
            check=True,
            text=True
        )

    # Remove LOAD/INFO lines
    with open(gadget_path, "r") as f:
        lines = f.readlines()
    with open(gadget_path, "w") as f:
        for line in lines:
            if not pattern.search(line):
                f.write(line)

    return gadget_path

def main():
    url_prefix = "https://archive.ubuntu.com/ubuntu/pool/main/g/glibc/"
    download_dir = '../GlibcDownloads'
    gadgets_dir = '../Gadgets/Ubuntu'

    soup = setup_environment(url_prefix, download_dir, gadgets_dir)

    match = re.compile(
        r"^libc6(-[a-z0-9]+)?_[0-9].*_(amd64|amd64v3|i386|arm64|armhf|x32)\.deb$"
    )
    skip = re.compile(r"(-dev|-dbg|-bin|-doc|-locale|-prof|_all\.deb$)")
    pattern = re.compile(r"\[LOAD\]|\[INFO\]", re.IGNORECASE)

    cutoff_date = datetime(2020, 1, 1).date()
    session = requests.Session()
    count = 0

    for link in soup.find_all("a", href=True):
        name = link.text.strip()

        ok, file_date = should_process_file(
            name, skip, cutoff_date, link, url_prefix, session
        )
        if not ok:
            continue

        if not match.match(name):
            continue

        # Determine future gadget filename BEFORE downloading
        parts = name.split("_")
        version = parts[1].replace("-", "_")
        arch = parts[2].replace(".deb", "")
        new_filename = f"glibc_{version}_{arch}.txt"
        arch_dir = os.path.join(gadgets_dir, arch)
        gadget_path = os.path.join(arch_dir, new_filename)

        # Skip if gadget already exists
        if os.path.exists(gadget_path):
            print(f"Already exists — skipping download: {new_filename}")
            continue

        # Otherwise proceed normally
        file_path = download_deb(name, url_prefix, download_dir)
        count += 1

        libc_path = extract_libc(file_path)
        generate_gadget_file(name, libc_path, gadgets_dir, arch, pattern)

    try:
        shutil.rmtree(download_dir)
        print(f"Removed download directory: {download_dir}")
    except OSError as e:
        print(f"Error removing {download_dir}: {e.strerror}")

    print(f"\nDone — {count} files downloaded to {download_dir}")

if __name__ == "__main__":
    main()
