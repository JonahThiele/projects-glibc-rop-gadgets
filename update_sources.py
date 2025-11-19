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



#Function to generate new html for version/architectures to display in index.html 
#based on source text files found in local directory
# Function to generate new HTML using discovered distros, versions, and architectures
def generate_html(distro_data):
    # Combine all options across distros (so UI shows everything available)
    all_arches = sorted({a for d in distro_data.values() for a in d["architectures"]})
    all_glibc_versions = sorted({v for d in distro_data.values() for v in d["glibc_versions"]})
    all_distro_versions = sorted({v for d in distro_data.values() for v in d["distro_versions"]})

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

        <div class="options-container">

            <div class="option-group">
                <h3>Distro</h3>
                {"".join(f'<label><input type="radio" name="distro" value="{d}"> {d}</label><br>' for d in distro_data.keys())}
            </div>

            <div class="option-group">
                <h3>Distro Version</h3>
                {"".join(f'<label><input type="radio" name="distrover" value="{dv}"> {dv}</label><br>' for dv in all_distro_versions)}
            </div>

            <div class="option-group">
                <h3>Glibc Version</h3>
                {"".join(f'<label><input type="radio" name="glibc" value="{gv}"> {gv}</label><br>' for gv in all_glibc_versions)}
            </div>

            <div class="option-group">
                <h3>Architecture</h3>
                {"".join(f'<label><input type="radio" name="arch" value="{a}"> {a}</label><br>' for a in all_arches)}
            </div>

        </div>

        <div class="input-container">
            <input type="text" id="autocomplete-input" placeholder="Start typing..." autocomplete="off">
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
    
    # Generate the HTML file with the found options
    generate_html(distro_data)
    print("index.html has been updated with available options.")

if __name__ == "__main__":
    main()
