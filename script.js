// =====================
// Trie Node & Trie (ROP gadgets) - unchanged from old working version
class TrieNode {
    constructor() {
        this.children = {};
        this.isEndOfWord = false;
        this.address = null;
    }
}

class Trie {
    constructor() {
        this.root = new TrieNode();
    }

    insert(line) {
        const parts = line.split(":");
        if (parts.length < 2) return;
        const address = parts[0].trim();
        const instruction = parts[1].trim();

        let currentNode = this.root;
        for (const char of instruction) {
            if (!currentNode.children[char]) currentNode.children[char] = new TrieNode();
            currentNode = currentNode.children[char];
        }
        currentNode.isEndOfWord = true;
        currentNode.address = address;
    }

    search(prefix) {
        let currentNode = this.root;
        for (const char of prefix) {
            if (!currentNode.children[char]) return [];
            currentNode = currentNode.children[char];
        }
        const matches = this._findInstructionsFromNode(currentNode, prefix);
        const avlTree = new AVLTree();
        matches.forEach(m => avlTree.insert(m));
        return avlTree.inOrderTraversal();
    }

    searchRegex(pattern) {
        if (!pattern) return [];
        let regex;
        try {
            regex = new RegExp(pattern, "i");
        } catch (e) {
            console.error("Invalid regex:", e);
            return [];
        }
        const allInstructions = this._findInstructionsFromNode(this.root, "");
        const matches = allInstructions.filter(item => regex.test(item.instruction));
        const avlTree = new AVLTree();
        matches.forEach(m => avlTree.insert(m));
        return avlTree.inOrderTraversal();
    }

    _findInstructionsFromNode(node, prefix) {
        let results = [];
        if (node.isEndOfWord) results.push({ address: node.address, instruction: prefix });
        for (const char in node.children) {
            results = results.concat(this._findInstructionsFromNode(node.children[char], prefix + char));
        }
        return results;
    }
}

// AVL stuff
class AVLNode {
    constructor(data) {
        this.data = data;
        this.left = null;
        this.right = null;
        this.height = 1;
    }
}

class AVLTree {
    constructor() { this.root = null; }

    getHeight(node) { return node ? node.height : 0; }
    updateHeight(node) { if (node) node.height = 1 + Math.max(this.getHeight(node.left), this.getHeight(node.right)); }
    getBalanceFactor(node) { return node ? this.getHeight(node.left) - this.getHeight(node.right) : 0; }
    rightRotate(y) {
        const x = y.left;
        const middle = x ? x.right : null;
        if (x) x.right = y;
        y.left = middle;
        this.updateHeight(y);
        this.updateHeight(x);
        return x;
    }
    leftRotate(x) {
        const y = x.right;
        const middle = y ? y.left : null;
        if (y) y.left = x;
        x.right = middle;
        this.updateHeight(x);
        this.updateHeight(y);
        return y;
    }
    insert(data) { this.root = this._insert(this.root, data); }
    _insert(node, data) {
        if (!node) return new AVLNode(data);
        if (data.instruction.length < node.data.instruction.length) node.left = this._insert(node.left, data);
        else node.right = this._insert(node.right, data);

        this.updateHeight(node);
        const balance = this.getBalanceFactor(node);

        if (balance > 1 && data.instruction.length < node.left.data.instruction.length) return this.rightRotate(node);
        if (balance < -1 && data.instruction.length > node.right.data.instruction.length) return this.leftRotate(node);
        if (balance > 1 && data.instruction.length > node.left.data.instruction.length) {
            node.left = this.leftRotate(node.left);
            return this.rightRotate(node);
        }
        if (balance < -1 && data.instruction.length < node.right.data.instruction.length) {
            node.right = this.rightRotate(node.right);
            return this.leftRotate(node);
        }

        return node;
    }

    inOrderTraversal(node = this.root, result = []) {
        if (node) {
            this.inOrderTraversal(node.left, result);
            result.push(node.data);
            this.inOrderTraversal(node.right, result);
        }
        return result;
    }
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        console.log('Address copied to clipboard:', text);
    }).catch(err => console.error('Failed to copy address:', err));
}

function showNotification(message, isError = false) {
    const notification = document.createElement('div');
    notification.textContent = message;
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.left = '50%';
    notification.style.transform = 'translateX(-50%)';
    notification.style.padding = '15px 25px';
    notification.style.borderRadius = '5px';
    notification.style.backgroundColor = isError ? '#ff4444' : '#4CAF50';
    notification.style.color = 'white';
    notification.style.boxShadow = '0 4px 8px rgba(0,0,0,0.2)';
    notification.style.zIndex = '1000';
    notification.style.fontFamily = 'Arial, sans-serif';
    notification.style.fontSize = '16px';
    notification.style.transition = 'opacity 0.5s ease-in-out';
    notification.style.opacity = '0';

    document.body.appendChild(notification);
    setTimeout(() => notification.style.opacity = '1', 10);
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => document.body.removeChild(notification), 500);
    }, 3000);
}

// Main DOM setup
document.addEventListener("DOMContentLoaded", () => {
    const finderInput = document.getElementById("file-finder-input");
    const finderResults = document.getElementById("file-finder-results");
    const gadgetInput = document.getElementById("autocomplete-input");
    const resultsList = document.getElementById("autocomplete-results");

    let loadedFiles = {};
    let selectedFilePath = null;

// Fuse.js for file search
// Convert FILE_INDEX into objects to separate name and file path
const fileObjects = FILE_INDEX.map(path => ({
    name: path.split("/").pop(),   // "glibc_2.31_20.04_x86_64.txt"
    fullPath: path                 // "Ubuntu/x86_64/glibc_2.31_20.04_x86_64.txt"
}));

// Fuse indexes ONLY the filename
const fuse = new Fuse(fileObjects, {
    keys: ["name"],
    threshold: 0.4,
    ignoreLocation: true
});

finderInput.addEventListener("input", () => {
    const query = finderInput.value.trim();
    finderResults.innerHTML = "";
    if (!query) return;

    const results = fuse.search(query).slice(0, 40);
    if (results.length === 0) {
        finderResults.style.display = "none";
        return;
    }

    results.forEach(({ item }) => {
        const li = document.createElement("li");
        li.textContent = item.name;  // show only filename

        li.addEventListener("click", () => {
            finderInput.value = item.name;
            finderResults.innerHTML = "";

            // Use the full path when loading the file
            selectedFilePath = "Gadgets/" + item.fullPath;

            loadGadgetFile(selectedFilePath);
        });

        finderResults.appendChild(li);
    });

    finderResults.style.display = "block";
});

    // Load gadget file into Trie
    async function loadGadgetFile(fullPath) {
        try {
            const response = await fetch(fullPath);
            const text = await response.text();
            const lines = text.split("\n").filter(Boolean);

            const trie = new Trie();
            lines.forEach(line => trie.insert(line));
            loadedFiles[fullPath] = trie;

            showNotification(`Loaded gadget file: ${fullPath}`);
        } catch (err) {
            console.error(err);
            showNotification("Failed to load gadget file", true);
        }
    }

    // Gadget input search (Trie)
    gadgetInput.addEventListener("input", () => {
        if (!selectedFilePath) return;
        const trie = loadedFiles[selectedFilePath];
        if (!trie) return;

        const query = gadgetInput.value.trim();
        if (!query) {
            resultsList.innerHTML = "";
            resultsList.style.display = "none";
            return;
        }

        //Some of the special RegEx chars are casuing issues with the search. I've removed them
        // For now, but This needs to be addressed.
        //const isRegex = /[\\^$*?.()|\{}]/.test(query);  // Detect if query has regex special chars
        const isRegex = /[\\^$*+?.()|[\]{}]/.test(query); //change to include text??!
        let matches = [];
        try {
            if (isRegex) {
                //change to search past the hex addr
                // Create a regex from the query. Ensure case-insensitive flag if needed
                const regex = new RegExp(query, "i"); // "i" for case insensitive search
                matches = trie.searchRegex(query); // Continue with Regex search from Trie
                matches = matches.filter(match => regex.test(match.instruction)); // Filter results using the regex
            } else {
                // Regular prefix-based search if no regex was used
                matches = trie.search(query);
            }
        } catch {
            matches = [];
            showNotification("Error during search", true);
        }

        resultsList.innerHTML = "";
        if (matches.length === 0) {
            resultsList.style.display = "none";
            return;
        }

        matches.slice().forEach(match => {
            const li = document.createElement("li");
            li.textContent = `${match.address}: ${match.instruction}`;
            li.addEventListener("click", () => {
                gadgetInput.value = match.instruction;
                resultsList.style.display = "none";
                copyToClipboard(match.address);
                showNotification("Copied address to clipboard!");
            });
            li.title = "Click to select instruction and copy address";
            resultsList.appendChild(li);
        });
        resultsList.style.display = "block";
    });
});
