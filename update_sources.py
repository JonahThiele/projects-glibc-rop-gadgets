import os
import re

GADGETS_DIR = "Gadgets/Ubuntu"

#Function to determine what architechtures and versions are present based on text files
#present in local directory
def extract_options_from_files():
    architectures = set()
    versions = set()
    
    # glibc_<glibcVersion>_<DistroVersion>_<arch>.txt
    pattern = re.compile(r"^glibc_([^_]+)_([^_]+)_([^_]+)\.txt$")
    
    # Walk through each architecture subfolder
    for arch in os.listdir(GADGETS_DIR):
        arch_path = os.path.join(GADGETS_DIR, arch)
        if not os.path.isdir(arch_path):
            continue
        architectures.add(arch)

    #Search local directory for files matching RegEx pattern
    #Note appropriate architectures and versions based on what is found
        for filename in os.listdir(arch_path):
            match = pattern.match(filename)
            if match:
                version = match.group(1)
                versions.add(version)
    
    #Return architectures and versions that were found in files in local directory
    return sorted(architectures), sorted(versions)

#Function to generate new html for version/architectures to display in index.html 
#based on source text files found in local directory
def generate_html(architectures, versions):
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
                <label><input type="radio" name="distro" value="Ubuntu"> Ubuntu</label><br>
                <label><input type="radio" name="distro" value="Fedora"> Fedora</label><br>
            </div>

            <div class="option-group">
                <h3>Glibc Version</h3>
                {"".join(f'<label><input type="radio" name="version" value="{version}"> {version}</label><br>' for version in versions)}
            </div>
            
            <div class="option-group">
                <h3>Architecture</h3>
                {"".join(f'<label><input type="radio" name="arch" value="{arch}"> {arch}</label><br>' for arch in architectures)}
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
    architectures, versions = extract_options_from_files()
    
    if not architectures or not versions:
        print("No valid architecture-version files found in directory.")
        return

    #If architectures and/or versions are found, generate new index.html
    
    print(f"Found architectures: {', '.join(architectures)}")
    print(f"Found versions: {', '.join(versions)}")
    
    # Generate the HTML file with the found options
    generate_html(architectures, versions)
    print("index.html has been updated with available options.")

if __name__ == "__main__":
    main()
