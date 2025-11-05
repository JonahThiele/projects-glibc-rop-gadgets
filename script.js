//Trie Node Object: a typical trie-type node with addition of a special variable "address"
//which stores the address of the ROP gadget in leaf nodes
class TrieNode {
    constructor() {
        this.children = {};
        this.isEndOfWord = false;
        this.address = null;  // Store the address here
    }
}

//Trie class
class Trie {
    constructor() {
        this.root = new TrieNode();
    }

    // Insert a complete ROP gadget instruction into the trie
    insert(line) {
        // Split the line into address and instruction part
        const parts = line.split(":");
        if (parts.length < 2) return; // Skip if the line doesn't contain a colon

        const address = parts[0].trim();  // Hex address before the colon (whitespace trimmed out)
        const instruction = parts[1].trim();  // Instruction after the colon (whitespace trimmed out)

        let currentNode = this.root;
        
        // Insert the instruction part of the line into the trie
        // by iterating through each char of the instruction and following it
        // down the trie (adding nodes as neccessary).
        for (const char of instruction) {
            // If the current doesn't have a node for the target char add one
            if (!currentNode.children[char]) {
                currentNode.children[char] = new TrieNode();
            }
            // Follow the branch given by the target char
            currentNode = currentNode.children[char];
        }

        // Once we have iterated through the entire instruction, we will mark the last (current)
        // node as the end of an instruction and store the address of the ROP gadget in
        // this (current) node's address variable.
        currentNode.isEndOfWord = true;
        currentNode.address = address;  // Store the address in the node
    }

    // Search trie for a given "prefix" of ROP gadget instruction string
    search(prefix) {
        // Start at root, as per usual
        let currentNode = this.root;

        // Search for the instruction prefix of in the trie
        // by iterating through each char of the instruction and following it
        // down the trie.
        for (const char of prefix) {
            // If current node is a leaf node, return empty array as failure to find prefix
            if (!currentNode.children[char]) {
                return [];
            }

            // Follow the branch given by target char
            currentNode = currentNode.children[char];
        }

        // If entire prefix has been followed successfully through trie, get 
        // a list of all full instruction matches(subtree branches) that descend from this prefix
	const matches = this._findInstructionsFromNode(currentNode, prefix);

	// Sort matches by instruction length using AVL tree
	// Create a new AVL tree that will be used to sort matches by length
	const avlTree = new AVLTree();

	//Add all matches to AVL tree (thus sorting them by length)
	matches.forEach(match => avlTree.insert(match));

	//Return an in-order traversal of the full AVL match tree
	//This should now return a list of rop-gadgets in order of length
	return avlTree.inOrderTraversal();

        // If entire prefix has been followed successfully through trie, return 
        // a list of all full instructions (subtree branches) that descend from this prefix
        //return this._findInstructionsFromNode(currentNode, prefix);
    }

    // Alternative method to search using regular expressions
    searchRegex(pattern) {
        // If the pattern is empty, return empty array
        if (!pattern) return [];
        
        let regex;
        try {
            // Create javascript regex object from pattern (case insensitive)
	    // https://www.w3schools.com/jsref/jsref_obj_regexp.asp
            regex = new RegExp(pattern, 'i');
        } catch (e) {
            // If invalid regex, return empty array
            console.error("Invalid regex:", e);
            return [];
        }
        
        // Get all instructions from the trie
        const allInstructions = this._findInstructionsFromNode(this.root, '');
        
        // Filter instructions that match the regex
        const matches = allInstructions.filter(item => regex.test(item.instruction));

	// Sort matches by instruction length using AVL tree
	// Create a new AVL tree that will be used to sort matches by length
	const avlTree = new AVLTree();

	//Add all matches to AVL tree (thus sorting them by length)
	matches.forEach(match => avlTree.insert(match));

	//Return an in-order traversal of the full AVL match tree
	//This should now return a list of rop-gadgets in order of length
	return avlTree.inOrderTraversal();

    }

    // This is a somewhat specialized recursive function/method that may not be necessary
    // in many tries, but was required for the specific application that this trie was
    // to be used for. It starts at a given node (and the prefix which leads to it), 
    // and recursively searches through every
    // child subtree, collecting complete instructions as it goes. The end result is
    // to give all complete instructions (along with the addresses at which those instructions
    // are located) that are 'descended' from a given node/prefix.
    _findInstructionsFromNode(node, prefix) {
        // Initialize array to store resulting instructions
        let results = [];

        //BASE CASE
        // If we've reached a leaf node (end of a complete instruction) then 
        // add the instruction, along with it's address, to the results array.
        if (node.isEndOfWord) {
            results.push({ address: node.address, instruction: prefix });
        }

        //RECURSIVE CASE
        // For every child of the current node, make a recursive call to find all
        // full instructions from that child on down.
        for (const char in node.children) {
            results = results.concat(this._findInstructionsFromNode(node.children[char], prefix + char));
        }

        //Once all children have been accounted for, return results array
        return results;
    }
}

//AVL Tree Node Object: a typical AVL/Binary Tree-type node
class AVLNode {
    constructor(data) {
        this.data = data;
        this.left = null;
        this.right = null;
        this.height = 1;
    }
}

//AVL Tree Class
class AVLTree {
    constructor() {
        this.root = null;
    }

    //Method to get the height of a given node
    getHeight(node) {
        //return node ? node.height : 0;
	if( node == null ){
		return 0;
	}
	return node.height
    }

    //Function/method to update the height of a given node
    updateHeight(node) {
	//If node exists, then set the new height to one plus the height of the larger of its subtrees
        if (node) {
            node.height = 1 + Math.max(
                this.getHeight(node.left),
                this.getHeight(node.right)
            );
        }
    }

    //Function/method to get the balance factor of a given node (subtree height difference)
    getBalanceFactor(node) {
        //return node ? this.getHeight(node.left) - this.getHeight(node.right) : 0;
	if( node == null ){
		return 0;
	}
	return this.getHeight(node.left) - this.getHeight(node.right);
    }

    //Perform a right rotation on given node
    rightRotate(y) {
        const x = y.left;
        //const middle_branch = x ? x.right : null;

	//If the node has a left child, set the 'middle_branch' to the right subtree of the left child 
	//Otherwise set the 'middle branch' to null
	var middle_branch = null;
	if( x != null ){
		middle_branch = x.right;
	}
	else{
		middle_branch = null;
	}

        // Perform rotation
        if (x) x.right = y;
        y.left = middle_branch;

        // Update heights
        this.updateHeight(y);
        this.updateHeight(x);

	//New root
        return x;
    }

    //Perform a left rotation on given node
    leftRotate(x) {
        const y = x.right;
        //const middle_branch = y ? y.left : null;
	//If the node has a right child, set the 'middle_branch' to the left subtree of the right child 
	//Otherwise set the 'middle branch' to null
	var middle_branch = null;
	if( y != null ){
		middle_branch = y.left;
	}
	else{
		middle_branch = null;
	}

        // Perform rotation
        if (y) y.left = x;
        x.right = middle_branch;

        // Update heights
        this.updateHeight(x);
        this.updateHeight(y);

        return y;
    }

    //Javascript helper insert method to protect root
    insert(data) {
        this.root = this._insert(this.root, data);
    }

    //Insert a node into the AVL tree
    _insert(node, data) {
        // 1. Perform normal BST insertion
        if (!node) return new AVLNode(data);

        if (data.instruction.length < node.data.instruction.length) {
            node.left = this._insert(node.left, data);
        } 
	else {
            node.right = this._insert(node.right, data);
        }

        // 2. Update height
        this.updateHeight(node);

        // 3. Get balance factor
        const balance = this.getBalanceFactor(node);

	// If the node becomes unbalanced, then there are 4 cases

        // 4. Handle unbalanced cases
        // Left Left
        if (balance > 1 && data.instruction.length < node.left.data.instruction.length) {
            return this.rightRotate(node);
        }
        // Right Right
        if (balance < -1 && data.instruction.length > node.right.data.instruction.length) {
            return this.leftRotate(node);
        }
        // Left Right
        if (balance > 1 && data.instruction.length > node.left.data.instruction.length) {
            node.left = this.leftRotate(node.left);
            return this.rightRotate(node);
        }
        // Right Left
        if (balance < -1 && data.instruction.length < node.right.data.instruction.length) {
            node.right = this.rightRotate(node.right);
            return this.leftRotate(node);
        }

        return node;
    }

    //Typical binary tree in order traversal method
    inOrderTraversal(node = this.root, result = []) {
        if (node) {
            this.inOrderTraversal(node.left, result);
            result.push(node.data);
            this.inOrderTraversal(node.right, result);
        }
        return result;
    }
}

// Helper function to copy text to clipboard
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        console.log('Address copied to clipboard:', text);
    }).catch(err => {
        console.error('Failed to copy address:', err);
    });
}

// Function to show a styled notification message
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
    
    // Fade in
    setTimeout(() => {
        notification.style.opacity = '1';
    }, 10);
    
    // Fade out and remove after 3 seconds
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 500);
    }, 3000);
}

//Main event listenter
document.addEventListener("DOMContentLoaded", function () {
    //Initialize html page elements
    const inputField = document.getElementById("autocomplete-input");
    const resultsList = document.getElementById("autocomplete-results");
    const versionRadios = document.querySelectorAll('input[name="version"]');
    const archRadios = document.querySelectorAll('input[name="arch"]');

    //Initialize Trie data structure 
    const trie = new Trie();
    let currentDataLoaded = false;

    // Helper functions to get selected glibc version
    function getSelectedVersion() {
        for (const radio of versionRadios) {
            if (radio.checked) {
                return radio.value;
            }
        }
        return null;
    }

    // Helper functions to get selected architechture
    function getSelectedArch() {
        for (const radio of archRadios) {
            if (radio.checked) {
                return radio.value;
            }
        }
        return null;
    }

    // Determine filename based on selected options + naming convention: "[arch]-[version].txt"
    function getDataFilename() {
        const version = getSelectedVersion();
        const arch = getSelectedArch();
        
        if (version && arch) {
            // Match new directory + filename pattern
            return `Gadgets/${arch}/libc6_${version}_${arch}.txt`;
        }
        return null;
    }

    // Load data from appropriate file based on selections
    function loadData() {
	//Construct filename from radio button selections
        const filename = getDataFilename();

	//If file doesn't exist, give error message
        if (!filename) {
            console.log("No version/arch selected");
            return;
        }

	//Reset the Trie data structure
        trie.root = new TrieNode(); 
        currentDataLoaded = false;

        fetch(filename)
            .then(response => response.text())
            .then(data => {
                const lines = data.split("\n");
                console.log(`Data loaded from ${filename}:`, lines);
                lines.forEach(line => {
                    trie.insert(line.trim());
                });
                currentDataLoaded = true;
            })
            .catch(error => {
                console.error(`Error loading ${filename}:`, error);
            });
    }

    // Add event listeners to radio buttons
    versionRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.checked) {
                loadData();
            }
        });
    });

    archRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.checked) {
                loadData();
            }
        });
    });

    /*
    // Handle input events for autocomplete
    const handleInputChange = function () {
        // Check if both version and architecture are selected
        const versionSelected = getSelectedVersion();
        const archSelected = getSelectedArch();
        
	//If user has not selected both a version and an architechture, then show an error message
        if (!versionSelected || !archSelected) {
            showNotification('Please select both a glibc version and architecture before searching', true);
            inputField.value = '';
            resultsList.style.display = 'none';
            resultsList.innerHTML = '';
            return;
        }

	//If data wasn't loaded, then show an error message
        if (!currentDataLoaded) {
            showNotification('Error: data not loaded!', true);
            inputField.value = '';
            resultsList.style.display = 'none';
            resultsList.innerHTML = '';
            return;
        }

	//Check for input field changes
        const query = inputField.value.trim();
        console.log("Input changed:", query);

	//If all input is cleared, then remove results box
        if (query.length === 0) {
            resultsList.style.display = 'none';
            resultsList.innerHTML = '';
            return;
        }

	//Get search matches from trie data structure and display results
        const matches = trie.search(query);
        displayResults(matches);
    };
    */

    // Modified handleInputChange function
    const handleInputChange = function () {
        // Check if both version and architecture are selected
        const versionSelected = getSelectedVersion();
        const archSelected = getSelectedArch();
        
	//If user has not selected both a version and an architechture, then show an error message
        if (!versionSelected || !archSelected) {
            showNotification('Please select both a glibc version and architecture before searching', true);
            inputField.value = '';
            resultsList.style.display = 'none';
            resultsList.innerHTML = '';
            return;
        }

        if (!currentDataLoaded) {
            resultsList.style.display = 'none';
            resultsList.innerHTML = '';
            return;
        }

	//Check for input field changes
        const query = inputField.value.trim();
        console.log("Input changed:", query);

	//If all input is cleared, then remove results box
        if (query.length === 0) {
            resultsList.style.display = 'none';
            resultsList.innerHTML = '';
            return;
        }

        // Determine if the query is a regex (contains special regex chars)
        const isRegex = /[\\^$*+?.()|[\]{}]/.test(query);

	// list of matching ROP gadgets
        let matches;

	//Determine if we need to use 'regex search' or normal 'prefix search'
        if (isRegex) {
            try {
                matches = trie.searchRegex(query);
                // Show a hint that regex search is being used
                if (query.length > 0 && matches.length > 0) {
                    showNotification('Searching by RegEx', false);
                }
            } catch (e) {
                matches = [];
                showNotification('Invalid regular expression', true);
            }
        } else {
            // Normal prefix search
	    showNotification('Searching by Prefix', false);
            matches = trie.search(query);
        }

        displayResults(matches);
    };

    //Event listener to check for/handle changes to input
    inputField.addEventListener("input", handleInputChange);

    // Display the autocomplete results 
    function displayResults(matches) {
        resultsList.innerHTML = '';
        if (matches.length === 0) {
            resultsList.style.display = 'none';
            return;
        }

        // The following code is meant to limit the number of matches to 10.
	// I ultimately decided it was better for user experience to not limit the results, however,
	// I have left this code here, so that the limit can easily be reinstated at a later date.
        // const limitedMatches = matches.slice(0, 10);
        const limitedMatches = matches.slice();

        limitedMatches.forEach(match => {
            const li = document.createElement('li');
            li.textContent = `${match.address}: ${match.instruction}`;

            // Add click handler that does both selection and copying
            li.addEventListener('click', function (e) {
                // Select the instruction in the input field
                inputField.value = match.instruction;
                resultsList.style.display = 'none';
                
                // Copy the address to clipboard
                copyToClipboard(match.address);
                
                // Show notification
                showNotification('Copied address to clipboard!');
            });

            // Add tooltip to explain the functionality
            li.title = "Click to select instruction and copy address";

            resultsList.appendChild(li);
        });

        resultsList.style.display = 'block';
    }
});
