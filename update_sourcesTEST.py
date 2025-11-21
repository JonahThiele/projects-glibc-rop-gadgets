import os
import re

#List of supported distros
DISTROS = ["Ubuntu", "Fedora"]

#Base folder where gadget files are organized
BASE_DIR = "Gadgets"

#Function to determine what architechtures and versions are present based on text files
#present in local directory
# Function to determine what architectures, versions, and distro versions
# exist based on filename patterns.
def extract_options_from_files():
    distro_data = {}

    # glibc_<glibcVersion>_<distroVersion>_<arch>.txt
    pattern = re.compile(r"^glibc_([^_]+)_([^_]+)_([^_]+)\.txt$")

    for distro in DISTROS:
        distro_path = os.path.join(BASE_DIR, distro)

        if not os.path.isdir(distro_path):
            continue

        architectures = set()
        glibc_versions = set()
        distro_versions = set()

        for arch in os.listdir(distro_path):
            arch_path = os.path.join(distro_path, arch)
            if not os.path.isdir(arch_path):
                continue

            architectures.add(arch)

            for filename in os.listdir(arch_path):
                m = pattern.match(filename)
                if m:
                    glibc_versions.add(m.group(1))
                    distro_versions.add(m.group(2))

        if architectures and glibc_versions and distro_versions:
            distro_data[distro] = {
                "architectures": sorted(architectures),
                "glibc_versions": sorted(glibc_versions),
                "distro_versions": sorted(distro_versions)
            }

    return distro_data


def collect_all_file_paths(distro_data):
    files = []
    for distro, info in distro_data.items():
        for arch in info["architectures"]:
            arch_path = os.path.join(BASE_DIR, distro, arch)
            for filename in os.listdir(arch_path):
                if filename.endswith(".txt"):
                    files.append(f"{distro}/{arch}/{filename}")
    return files


#Function to generate new html for version/architectures to display in index.html 
#based on source text files found in local directory
# Function to generate new HTML using discovered distros, versions, and architectures
def generate_html(distro_data):

    html_template = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ROP Gadget Autocomplete</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div class="container">
        <h1>ROP Gadget Autocomplete</h1>

        <div class="input-container">

            <!-- Search bar for what file -->
            <input type="text" id="file-finder-input" placeholder="Search for distro/version/arch..." autocomplete="off">
            <ul id="file-finder-results"></ul>

            <!-- Search bar for ROP gadgets -->
            <input type="text" id="autocomplete-input" placeholder="Search gadgets..." autocomplete="off">
            <ul id="autocomplete-results"></ul>

        </div>
    </div>

    <script src="script.js"></script>
</body>
</html>'''

    with open('index.html', 'w') as f:
        f.write(html_template)

def main():
    #Get architectures and versions from source filenames present in local directory
    distro_data = extract_options_from_files()
    
    if not distro_data:
        print("No valid architecture-version files found in directory.")
        return

    #If architectures and/or versions are found, generate new index.html
    for distro, data in distro_data.items():
        print(f"[{distro}] Architectures: {', '.join(data['architectures'])}")
        print(f"[{distro}] Glibc Versions: {', '.join(data['glibc_versions'])}")
        print(f"[{distro}] Distro Versions: {', '.join(data['distro_versions'])}")

    file_list = collect_all_file_paths(distro_data)

    with open("file_index.js", "w") as f:
        f.write("const FILE_INDEX = ")
        f.write(json.dumps(file_list, indent=4))
        f.write(";")
    
    # Generate the HTML file with the found options
    generate_html(distro_data)
    print("index.html has been updated with available options.")

if __name__ == "__main__":
    main()