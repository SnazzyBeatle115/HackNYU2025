/**
 * Farm Page JavaScript - Drag and Drop Tree Planting
 */

document.addEventListener('DOMContentLoaded', () => {
    const farmGrid = document.getElementById('farmGrid');
    const shopItems = document.querySelectorAll('.shop-item');
    const treesPlantedElement = document.getElementById('treesPlanted');
    const coinsElement = document.getElementById('coins');
    
    // Farm state
    let treesPlanted = 0;
    let coins = 1000;
    const gridSize = 8; // 8x8 grid
    let plantedTrees = {}; // Track planted trees by cell ID
    
    // Tree prices
    const treePrices = {
        'pine': 50,
        'oak': 75,
        'apple': 100,
        'cherry': 120
    };
    
    // Coin generation rates per second for each tree type
    const treeCoinRates = {
        'pine': 5,
        'oak': 8,
        'apple': 12,
        'cherry': 15
    };
    
    let coinGenerationInterval = null;
    
    // Initialize farm grid
    function initFarmGrid() {
        farmGrid.innerHTML = '';
        for (let row = 0; row < gridSize; row++) {
            for (let col = 0; col < gridSize; col++) {
                const cell = document.createElement('div');
                cell.className = 'farm-cell';
                cell.dataset.row = row;
                cell.dataset.col = col;
                cell.id = `cell-${row}-${col}`;
                
                // Allow dropping
                cell.addEventListener('dragover', handleDragOver);
                cell.addEventListener('drop', handleDrop);
                cell.addEventListener('dragenter', handleDragEnter);
                cell.addEventListener('dragleave', handleDragLeave);
                
                farmGrid.appendChild(cell);
            }
        }
    }
    
    // Set up drag events for shop items
    shopItems.forEach(item => {
        item.addEventListener('dragstart', handleDragStart);
        item.addEventListener('dragend', handleDragEnd);
    });
    
    // Drag start
    function handleDragStart(e) {
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', e.target.dataset.treeType || e.target.closest('.shop-item').dataset.treeType);
        e.target.classList.add('dragging');
    }
    
    // Drag end
    function handleDragEnd(e) {
        e.target.classList.remove('dragging');
        document.querySelectorAll('.farm-cell').forEach(cell => {
            cell.classList.remove('drag-over');
        });
    }
    
    // Drag over
    function handleDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';
    }
    
    // Drag enter
    function handleDragEnter(e) {
        e.preventDefault();
        e.target.classList.add('drag-over');
    }
    
    // Drag leave
    function handleDragLeave(e) {
        e.target.classList.remove('drag-over');
    }
    
    // Drop handler
    function handleDrop(e) {
        e.preventDefault();
        e.target.classList.remove('drag-over');
        
        const cell = e.target.closest('.farm-cell');
        if (!cell) return;
        
        const treeType = e.dataTransfer.getData('text/plain');
        const cellId = cell.id;
        
        // Check if cell is already occupied
        if (plantedTrees[cellId]) {
            showNotification('This spot is already occupied!', 'error');
            return;
        }
        
        // Check if player has enough coins
        const price = treePrices[treeType];
        if (coins < price) {
            showNotification(`Not enough coins! Need ${price} coins.`, 'error');
            return;
        }
        
        // Plant the tree
        plantTree(cell, treeType, cellId);
        
        // Deduct coins
        coins -= price;
        updateCoins();
        
        // Start coin generation if not already running
        startCoinGeneration();
        
        showNotification(`${treeType.charAt(0).toUpperCase() + treeType.slice(1)} tree planted!`, 'success');
    }
    
    // Plant a tree in a cell
    function plantTree(cell, treeType, cellId, incrementCounter = true) {
        const treeEmoji = {
            'pine': '🌲',
            'oak': '🌳',
            'apple': '🍎',
            'cherry': '🌸'
        };
        
        const treeElement = document.createElement('div');
        treeElement.className = `planted-tree ${treeType}-tree`;
        treeElement.dataset.treeType = treeType;
        treeElement.textContent = treeEmoji[treeType];
        
        // Add click to remove functionality
        treeElement.addEventListener('click', () => {
            if (confirm('Remove this tree?')) {
                removeTree(cellId, treeType);
            }
        });
        
        cell.appendChild(treeElement);
        plantedTrees[cellId] = treeType;
        
        // Only increment counter if this is a new tree (not a restored one)
        if (incrementCounter) {
            treesPlanted++;
            updateTreesPlanted();
        }
        
        // Save to localStorage
        saveFarmState();
    }
    
    // Remove a tree
    function removeTree(cellId, treeType) {
        const cell = document.getElementById(cellId);
        const treeElement = cell.querySelector('.planted-tree');
        if (treeElement) {
            treeElement.remove();
            delete plantedTrees[cellId];
            treesPlanted--;
            updateTreesPlanted();
            saveFarmState();
            
            // Stop coin generation if no trees left
            if (Object.keys(plantedTrees).length === 0) {
                stopCoinGeneration();
            }
            
            showNotification('Tree removed!', 'info');
        }
    }
    
    // Generate coins from all planted trees
    function generateCoins() {
        let totalCoinsGenerated = 0;
        
        // Calculate coins from each planted tree
        Object.values(plantedTrees).forEach(treeType => {
            if (treeCoinRates[treeType]) {
                totalCoinsGenerated += treeCoinRates[treeType];
            }
        });
        
        if (totalCoinsGenerated > 0) {
            coins += totalCoinsGenerated;
            updateCoins();
            saveFarmState();
        }
    }
    
    // Start coin generation interval
    function startCoinGeneration() {
        if (coinGenerationInterval) {
            clearInterval(coinGenerationInterval);
        }
        // Generate coins every second
        coinGenerationInterval = setInterval(generateCoins, 1000);
    }
    
    // Stop coin generation interval
    function stopCoinGeneration() {
        if (coinGenerationInterval) {
            clearInterval(coinGenerationInterval);
            coinGenerationInterval = null;
        }
    }
    
    // Update coins display
    function updateCoins() {
        coinsElement.textContent = coins;
    }
    
    // Update trees planted display
    function updateTreesPlanted() {
        treesPlantedElement.textContent = treesPlanted;
    }
    
    // Save farm state to localStorage
    function saveFarmState() {
        const state = {
            trees: plantedTrees,
            coins: coins,
            treesPlanted: treesPlanted
        };
        localStorage.setItem('farmState', JSON.stringify(state));
    }
    
    // Load farm state from localStorage
    function loadFarmState() {
        const saved = localStorage.getItem('farmState');
        if (saved) {
            try {
                const state = JSON.parse(saved);
                plantedTrees = state.trees || {};
                coins = state.coins || 1000;
                
                // Calculate treesPlanted from actual number of trees
                treesPlanted = Object.keys(plantedTrees).length;
                
                // Restore planted trees
                Object.keys(plantedTrees).forEach(cellId => {
                    const cell = document.getElementById(cellId);
                    if (cell) {
                        plantTree(cell, plantedTrees[cellId], cellId, false); // false = don't increment counter
                    }
                });
                
                updateCoins();
                updateTreesPlanted();
            } catch (e) {
                console.error('Error loading farm state:', e);
            }
        }
    }
    
    // Show notification
    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `farm-notification ${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            background: ${type === 'error' ? '#f8d7da' : type === 'success' ? '#d4edda' : '#d1ecf1'};
            border: 4px solid ${type === 'error' ? '#721c24' : type === 'success' ? '#155724' : '#0c5460'};
            color: ${type === 'error' ? '#721c24' : type === 'success' ? '#155724' : '#0c5460'};
            border-radius: 0;
            z-index: 1000;
            box-shadow: 4px 4px 0px rgba(0,0,0,0.3);
            font-size: 0.7rem;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.transition = 'opacity 0.3s';
            notification.style.opacity = '0';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
    
    // Initialize
    initFarmGrid();
    loadFarmState();
    updateCoins();
    updateTreesPlanted();
    
    // Start coin generation if there are trees planted
    if (Object.keys(plantedTrees).length > 0) {
        startCoinGeneration();
    }
});

