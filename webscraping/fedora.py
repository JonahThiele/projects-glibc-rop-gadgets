#!/usr/bin/env python3
"""
Script to download and extract binaries for Fedora RPMs of
the glibc versions found on this home site: 
https://koji.fedoraproject.org/koji/packageinfo?buildStart=0&packageID=57&buildOrder=-completion_time&tagOrder=name&tagStart=0#buildlist
"""

import os
import re
import sys
import time
import shutil
import requests
import subprocess
from bs4 import BeautifulSoup
from collections import defaultdict
from urllib.parse import urljoin, urlparse, parse_qs, urlencode

def scrape_glibc_versions_from_page(url, version_dict):
    """
    Scrape glibc versions from a single page and update the version dictionary
    Returns True if any glibc links were found on the page
    Args:
        url (string): Page URL from which version links should be scraped
        version_dict (dict): Page URL from which version links should be scraped
    Returns:
        bool: whether or not an appropriate glibc url was found on this page
    """

    # Check connectivity
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching page {url}: {e}")
        return False
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # REGEX Pattern to match glibc version strings with fc disttag
    pattern = re.compile(r'glibc-(\d+\.\d+)-(\d+)\.(fc\d+)')
    
    glibc_found = False
    
    # Find all links that contain glibc version information
    for link in soup.find_all('a', href=True):
        link_text = link.get_text().strip()
        match = pattern.match(link_text)
        
        # If we have an 'fc' disttag link
        if match:
            glibc_found = True
            version = match.group(1)  # e.g., "2.41"
            release = int(match.group(2))  # e.g., 11
            disttag = match.group(3)  # e.g., "fc42"
            build_id = None
            
            # Extract build ID from href
            href = link['href']
            build_match = re.search(r'buildID=(\d+)', href)
            if build_match:
                build_id = build_match.group(1)
            
            # Store only if we have a build ID and it's an fc disttag
            # Note that the fc disttag represents a standard build 
            # (as opposed to the exprimental eln)
            if build_id and disttag.startswith('fc'):
                key = (version, disttag)
                
                # Keep only the lowest release number for each version-disttag combination
                # (If we want to change this to highest release number, we can easily do so here)
                if (key not in version_dict) or (release < version_dict[key]['release']):
                    version_dict[key] = {
                        'release': release,
                        'build_id': build_id,
                        'full_name': link_text,
                        'source_url': url
                    }
    
    return glibc_found

def get_glibc_versions_all_pages(quiet = False):
    """
    Extract glibc versions from all pages of the Fedora Koji package page
    Args:
        quiet (bool): Should the program display additional stdout information or not?
    Returns:
        dict: dictionary containing all glibc versions to be downloaded. Keys are tuples (version, disttag)
    """
    base_url = "https://koji.fedoraproject.org/koji/packageinfo?buildStart=0&packageID=57&buildOrder=-completion_time&tagOrder=name&tagStart=0#buildlist"
    
    version_dict = {}
    processed_urls = set()
    current_url = base_url
    page_count = 0
    
    if quiet == False:
        print("Starting to scrape glibc versions from all pages...")
    
    # Use iterative approach - follow next page links until no more glibc content
    while current_url and (current_url not in processed_urls):
        page_count += 1

        if quiet == False:
            print(f"Scraping page {page_count}: {current_url}")
        
        processed_urls.add(current_url)
        
        # Scrape the current page
        glibc_found = scrape_glibc_versions_from_page(current_url, version_dict)
        
        if not glibc_found:
            if quiet == False:
                print(f"No glibc links found on page {page_count}, stopping pagination.")

            # This maybe should be 'continue'... not sure, should double check behavior...
            break
        
        # Find the next page URL
        try:
            response = requests.get(current_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            next_url = None
            pagination_links = soup.find_all('a', href=True)
            
            for link in pagination_links:
                link_text = link.get_text().strip()
                href = link['href']
                
                # Look for next page indicators
                if '>>>' in link_text or '>>' in link_text or 'Next' in link_text.lower():
                    next_url = urljoin(current_url, href)
                    break
            
            # If no explicit next link found, try to construct next page URL
            if not next_url:
                parsed_url = urlparse(current_url)
                query_params = parse_qs(parsed_url.query)
                
                if 'buildStart' in query_params:
                    current_start = int(query_params['buildStart'][0])
                    next_start = current_start + 50
                    
                    # Update buildStart parameter
                    query_params['buildStart'] = [str(next_start)]
                    
                    # Reconstruct URL
                    new_query = urlencode(query_params, doseq=True)
                    next_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}?{new_query}{parsed_url.fragment}"
                else:
                    # If no buildStart parameter, we're probably on the first page
                    next_url = base_url.replace('buildStart=0', 'buildStart=50')
            
            # Avoid infinite loop by checking if we've seen this URL before
            if next_url in processed_urls:
                if quiet == False:
                    print("Next URL already processed, stopping pagination.")
                break
                
            current_url = next_url
            
            # Small delay to be respectful to the server
            time.sleep(0.5)
            
        except requests.RequestException as e:
            if quiet == False:
                print(f"Error fetching next page: {e}")
            break
    
    print(f"Scraped {page_count} pages total.")
    return version_dict

def extract_rpm_urls_from_buildinfo(buildinfo_url):
    """
    Extract RPM download URLs for specific architectures from buildinfo page
    Args:
        buildinfo_url (string): url for buildinfo page where the rpm download links are located
    Returns:
        dict: dictionary with string keys representing the architecture and values representing the .rpm download urls
    """

    # ARM 32 bit assembly didn't seem to be available on this repository, but 
    # if we find it, we should be able to add it later.
    target_architectures = ['aarch64', 'i686', 'x86_64']
    rpm_urls = {}
    
    # Check connectivity
    try:
        response = requests.get(buildinfo_url)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching buildinfo page {buildinfo_url}: {e}")
        return rpm_urls
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Look for all RPM download links
    for link in soup.find_all('a', href=True):
        href = link['href']
        
        # Check if this is an RPM download link for glibc (not debuginfo or other packages)
        if (href.endswith('.rpm') and 
            'glibc-' in href and 
            not any(exclude in href for exclude in ['debuginfo', 'debugsource', 'devel', 'headers', 'static', 'utils'])):
            
            # Check if it's for one of our target architectures
            for arch in target_architectures:
                # Look for architecture in the URL path
                if f'/{arch}/' in href and arch not in rpm_urls:
                    # Make sure it's the main glibc package, not subpackages
                    if re.search(rf'glibc-\d+\.\d+-\d+\.fc\d+\.{arch}\.rpm', href):
                        rpm_urls[arch] = href
                        break
    
    return rpm_urls

def generate_download_urls(version_dict, quiet = False):
    """
    Generate actual download URLs from the version dictionary
    Includes scraping RPM URLs from buildinfo pages
    Args:
        quiet (bool): Should the program display additional stdout information or not?
        version_dict (dict): dictionary containing all glibc versions to be downloaded. Keys are (version, disttag)
    Returns:
        list: list of dicts representing all rpm uls to be downloaded
    """
    base_url = "https://koji.fedoraproject.org/koji/"
    download_urls = []
    
    if quiet == False:
        print("\nExtracting RPM download links from buildinfo pages...")

    total_builds = len(version_dict)
    current_build = 0
    
    # For each key in verson_dict
    for (version, disttag), info in version_dict.items():
        current_build += 1
        build_id = info['build_id']
        full_name = info['full_name']
        
        # Construct the buildinfo URL
        # These are the actual links where the .rpm builds can be found
        buildinfo_url = urljoin(base_url, f"buildinfo?buildID={build_id}")
        
        if quiet == False:
            print(f"Processing build {current_build}/{total_builds}: {full_name}")
        
        # Extract RPM URLs from the buildinfo page
        # This will be a dict with keys that are architechture strings
        # and values that represent the rpm download URLs
        rpm_urls = extract_rpm_urls_from_buildinfo(buildinfo_url)
        
        # Small delay to be respectful to the server
        time.sleep(0.3)
        
        download_urls.append({
            'version': version,
            'disttag': disttag,
            'release': info['release'],
            'full_name': full_name,
            'buildinfo_url': buildinfo_url,
            'build_id': build_id,
            'source_page': info.get('source_url', 'Unknown'),
            'rpm_urls': rpm_urls
        })
    
    return download_urls

def fetch_rpm_urls_all_versions(quiet = False):
    """
    Generate actual download URLs from the version dictionary
    Includes scraping RPM URLs from buildinfo pages
    Args:
        quiet (bool): Should the program display additional stdout information or not?
    Returns:
        list: list representing all rpm uls to be downloaded
    """

    if quiet == False:
        print("Fetching glibc versions from all pages of Fedora Koji repository...")

    # version_dict looks like the following:

    #   version_dict[key] = {
    #       'release': release,
    #       'build_id': build_id,
    #       'full_name': link_text,
    #       'source_url': url
    #   }

    # and the key for version dict is a tuple as follows:
    #
    # key = (version, disttag)

    version_dict = get_glibc_versions_all_pages(quiet)
    
    if not version_dict:
        if quiet == False:
            print("No glibc versions found or error occurred.")
        return
    
    if quiet == False:
        print(f"\nFound {len(version_dict)} unique glibc version-disttag combinations across all pages")
    
    # Generate URLs including RPM download links
    urls = generate_download_urls(version_dict)

    # Note: the above is a list of dicts representing the rpm URLs to be downloaded
    # Each dict has the following structure
    #   {
    #       'version': version,
    #       'disttag': disttag,
    #       'release': info['release'],
    #       'full_name': full_name,
    #       'buildinfo_url': buildinfo_url,
    #       'build_id': build_id,
    #       'source_page': info.get('source_url', 'Unknown'),
    #       'rpm_urls': rpm_urls
    #   }
 
    
    # Sort by version and disttag
    urls.sort(key=lambda x: (x['version'], x['disttag']))
    
    if quiet == False:
        print("\n" + "=" * 120)
        print("LOWEST RELEASE FOR EACH GLIBC VERSION WITH FC DISTTAG")
        print("=" * 120)
        
    # Count architectures found
    arch_stats = defaultdict(int)
    
    for item in urls:
        if quiet == False:
            print(f"\nVersion: {item['version']:<8} Disttag: {item['disttag']:<6} Release: {item['release']:<4}")
            print(f"Full Name: {item['full_name']}")
            print(f"Build Info: {item['buildinfo_url']}")
            
        if item['rpm_urls']:
            if quiet == False:
                print("RPM Download URLs:")
            for arch, rpm_url in item['rpm_urls'].items():
                arch_stats[arch] += 1
                if quiet == False:
                    print(f"  {arch}: {rpm_url}")
        else:
            if quiet == False:
                print("RPM Download URLs: No compatible RPMs found for target architectures")
        
        if quiet == False:
            print("-" * 120)
    
    # Print summary statistics if necessary
    if quiet == False:
        print("\n" + "=" * 120)
        print("SUMMARY STATISTICS")
        print("=" * 120)
        print(f"Total unique glibc versions: {len(urls)}")
        for arch in ['aarch64', 'i686', 'x86_64']:
            print(f"Builds with {arch} RPM: {arch_stats[arch]}/{len(urls)}")
        
    # Generate a simple list of just the RPM URLs for scripting purposes
    if quiet == False:
        print("\n" + "=" * 120)
        print("FLAT LIST OF ALL RPM URLs (for scripting use)")
        print("=" * 120)

    # Append rpm URLs to list of URLs to be returned
    all_rpm_urls = []
    for item in urls:
        for arch, rpm_url in item['rpm_urls'].items():
            all_rpm_urls.append(rpm_url)
            if quiet == False:
                print(rpm_url)
    
    if quiet == False:
        print(f"\nTotal RPM URLs found: {len(all_rpm_urls)}")
    
    return all_rpm_urls
    
def download_rpms_all_version(quiet=False):
    urls = fetch_rpm_urls_all_versions(quiet)
    # Where we are downloading things (taken from Ubuntu script for consistency)
    download_dir = '../GlibcDownloads/Fedora'
    file_paths = []
    count = 0
    os.makedirs(download_dir, exist_ok=True)

    for url in urls:
        # Finding the name and path
        file_path = urlparse(url).path
        file_name = os.path.basename(file_path)
        full_path = os.path.join(download_dir, file_name)
        if quiet == False:
            print(f"Downloading: {file_name}")
        try:
            # Ubuntu group was using the requests library so I used this instead of the wget
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                with open(full_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            if quiet == False:
                print(f"Successfully downloaded: {file_name}\n")
            # The path to the rpm, formatted like this "../GlibcDownloads/Fedora/name.rpm"
            file_paths.append(full_path)
            count +=1

        except requests.exceptions.RequestException as e:
            if quiet == False:
                print(f"Error downloading {file_name}: {e}")

    print(f"Successfully downloaded {count} files")
    # I return this to make extracting easier later
    return file_paths
        
LIBC_PATHS = [ './usr/lib64/libc.so.6', './usr/lib/libc.so.6','./lib64/libc.so.6', './lib/libc.so.6' ]

def copy_binary(source_path, destination_path):
    """
    Copy a binary file from source to destination using shutil.copy()
    
    Args:
        source_path (str): Path to the source binary file
        destination_path (str): Path where the binary should be copied

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Check if source file exists
        if not os.path.exists(source_path):
            print(f"Error: Source file '{source_path}' does not exist")
            return False
        
        # Create destination directory if it doesn't exist
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        
        # Copy the file
        shutil.copy(source_path, destination_path)
        print(f"Successfully copied '{source_path}' to '{destination_path}'")
        return True
        
    except Exception as e:
        print(f"Error copying file: {e}")
        return False

def create_libc_filename(rpm_filename):
    """
    """
    # Match sequence of digits and dots that looks like a version number
    version_pattern = r'(\d+\.\d+(?:\.\d+)*)'

    match = re.search(version_pattern, rpm_filename)

    if match:
        version = match.group(1)
        return f"libc-{version}.so"
    else:
        raise ValueError(f"Could not extract version from filename: {rpm_filename}")

def extract_with_rpm2cpio(rpm_file, output_dir="."):
    """
    Extract using rpm2cpio and cpio commands via pipe
    Args:
        rpm_file (str): Path to the source rpm archive file
        output_dir (str): Path where the binary should be extracted
    """
    try:
        # Create rpm2cpio -> cpio pipeline
        rpm2cpio = subprocess.Popen(['rpm2cpio', rpm_file], stdout=subprocess.PIPE)

        # I've had to hard-code the possible paths to libc.so.6 here. Not ideal.
        # Maybe we can come up with a search solution later on
        cpio = subprocess.Popen(
            ['cpio', '-idmv', LIBC_PATHS[0], LIBC_PATHS[1], LIBC_PATHS[2], LIBC_PATHS[3], f"./lib/{create_libc_filename(rpm_file)}", f"./lib64/{create_libc_filename(rpm_file)}"],
            stdin=rpm2cpio.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=output_dir
        )
        
        #Close rpm2cpio standard output
        rpm2cpio.stdout.close()
        output, error = cpio.communicate()
        
        if cpio.returncode == 0:
            print("Successfully extracted libc.so.6")
            # Find where it was extracted
            for path in LIBC_PATHS:
                full_path = os.path.join(output_dir, path.lstrip('./'))
                if os.path.exists(full_path):
                    return full_path
        else:
            print(f"Error: {error.decode()}")
            
    except FileNotFoundError:
        print("Error: rpm2cpio or cpio not found. Install with:")
        print("sudo apt-get install rpm2cpio cpio")
    
    return None

def extract_all_rpms(quiet=False):
    # Gets a list of file paths of downloaded files
    files = download_rpms_all_version(quiet)
    # Makes a temp place to store binary
    binary_dir = "../GlibcDownloads/Fedora/Binaries"
    os.makedirs(binary_dir, exist_ok=True)
    name_list = []
    for f in files:
        result = extract_with_rpm2cpio(f, binary_dir)
        if result:
            print(f"Extracted to: {result}")
            # Ugly line that isolates just the filename, sans path and extention
            name = os.path.splitext(os.path.basename(f))[0]
            name_list.append(name + "_libc.so.6")
            # Could probably remove the if now, but I was having difficulties so I used it for error checking
            if not copy_binary(result, f"{binary_dir}/{name}_libc.so.6"): 
                print("Error with copy_binary, quiting")
        else:
            print("Extraction failed")
    return name_list

def create_rop_gadgets(quiet=False):
    # Make a subfolder for that architecture
    gadgets_dir = "../Gadgets/Fedora"
    binary_dir = "../GlibcDownloads/Fedora/Binaries"
    names = extract_all_rpms(quiet)
    for name in names:
        arch = name.split(".")[3].replace("_libc", "")
        arch_dir = os.path.join(gadgets_dir, arch)
        os.makedirs(arch_dir, exist_ok=True)
        glibc_version = name.split('-')[1]
        fedora_version = name.split('.')[2]
        gadget_path = os.path.join(arch_dir, "glibc_" + glibc_version + "_" + fedora_version + "_" + arch + ".txt")
        glibc_path = os.path.join(binary_dir, name)
        print(f"Running {name} through ropper to {gadget_path}")
        with open(gadget_path, "w") as out:
            subprocess.run(
                ["ropper", "--nocolor", "--file", glibc_path],
                stdout=out,
                stderr=subprocess.STDOUT,
                check=True,
                text=True)
        # remove first LOAD and INFO lines by copying the file into memory
        # probably a more efficient way of doing this but this should work
        # regex for reducing file size
        pattern = re.compile(r"\[LOAD\]|\[INFO\]", re.IGNORECASE)
        print(f"Attempting to remove junk from {gadget_path}")
        with open(gadget_path, "r") as f:
            lines = f.readlines()
        with open(gadget_path, "w") as f:
            for line in lines:
                if not pattern.search(line):
                    f.write(line)

    # Remove /GlibcDownloads (binaries) directory once it's no longer needed
    binary_abs_path = os.path.abspath("../GlibcDownloads")
    if not os.path.exists(binary_abs_path):
        raise FileNotFoundError(f"Directory not found: {binary_abs_path}")
    if not os.path.isdir(binary_abs_path):
        raise NotADirectoryError(f"Not a directory: {binary_abs_path}")
    shutil.rmtree(binary_abs_path)
        
    

def main():
    # Can pass 'q' (or anything else) as an command argument to force the program to run non-verbosely
    quiet = True
    if len(sys.argv) < 2:
        quiet = False

    create_rop_gadgets(quiet)

if __name__ == "__main__":
    main()