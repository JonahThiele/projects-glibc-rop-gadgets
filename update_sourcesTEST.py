import os
import re

# List of supported distros
DISTROS = ["Ubuntu", "Fedora"]

# Base folder where gadget files are organized
BASE_DIR = "Gadgets"

# Output files
FILE_INDEX_JS = "file_index.js"  # JS array containing all gadget file paths
INDEX_HTML = "index.html"        # Main HTML page for the autocomplete UI

def collect_gadget_files():
    """
    Return a sorted list of all valid gadget file paths relative to Gadgets/
    Filenames must match the pattern: glibc_<glibcVersion>_<distroVersion>_<arch>.txt
    """
    pattern = re.compile(r"^glibc_([^_]+)_([^_]+)_([^_]+)\.txt$")
    file_paths = []

    for distro in DISTROS:
        distro_path = os.path.join(BASE_DIR, distro)
        if not os.path.isdir(distro_path):
            continue  # Skip missing distro folders

        for arch in os.listdir(distro_path):
            arch_path = os.path.join(distro_path, arch)
            if not os.path.isdir(arch_path):
                continue  # Skip non-directory files

            for fname in os.listdir(arch_path):
                if pattern.match(fname):
                    # Include relative path from Gadgets/
                    file_paths.append(f"{distro}/{arch}/{fname}")

    return sorted(file_paths)

def generate_file_index_js(file_paths):
    """
    Generate a JavaScript file containing a FILE_INDEX array
    This is used by script.js for fuzzy file search
    """
    js_content = "const FILE_INDEX = [\n" + ",\n".join(f'    "{p}"' for p in file_paths) + "\n];\n"
    with open(FILE_INDEX_JS, "w") as f:
        f.write(js_content)
    print(f"[+] Generated {FILE_INDEX_JS} with {len(file_paths)} entries")

def generate_index_html():
    """
    Generate a simplified HTML page with:
    - Search bar for gadget files
    - Search bar for gadgets inside selected file
    - No more radio buttons; fuzzy search replaces them
    """
    html_content = '''<!DOCTYPE html>
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
            <h3>Search Gadget Files</h3>
            <input type="text" id="file-finder-input" placeholder="Start typing a file name..." autocomplete="off">
            <ul id="file-finder-results"></ul>
        </div>

        <div class="input-container">
            <h3>Search Gadgets Inside Selected File</h3>
            <input type="text" id="autocomplete-input" placeholder="Start typing a ROP gadget..." autocomplete="off">
            <ul id="autocomplete-results"></ul>
        </div>
    </div>

    <!-- Include generated file index for fuzzy file search -->
    <script src="https://cdn.jsdelivr.net/npm/fuse.js/dist/fuse.min.js"></script>
    <script src="file_index.js"></script>
    <script src="script.js"></script>
</body>
</html>'''

    with open(INDEX_HTML, "w") as f:
        f.write(html_content)
    print(f"[+] Generated {INDEX_HTML}")

def main():
    # Collect architectures and versions from source filenames present in local directory
    files = collect_gadget_files()
    if not files:
        print("[!] No gadget files found in Gadgets/ folder.")
        return

    # Generate JS array for fuzzy file search
    generate_file_index_js(files)

    # Generate new index.html with search bars
    generate_index_html()

if __name__ == "__main__":
    main()
