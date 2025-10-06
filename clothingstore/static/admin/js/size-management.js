document.addEventListener('DOMContentLoaded', function() {
    // Function to update the size type badge
    function updateSizeTypeBadge(selectElement) {
        const selectedOption = selectElement.options[selectElement.selectedIndex];
        const sizeType = selectedOption.getAttribute('data-size-type');
        let badge = selectElement.nextElementSibling;
        
        // Create badge if it doesn't exist
        if (!badge || !badge.classList.contains('size-type-badge')) {
            badge = document.createElement('span');
            badge.className = 'size-type-badge';
            selectElement.parentNode.insertBefore(badge, selectElement.nextSibling);
        }
        
        // Update badge content and style
        if (sizeType) {
            badge.textContent = sizeType.charAt(0).toUpperCase() + sizeType.slice(1);
            badge.style.display = 'inline-block';
        } else {
            badge.style.display = 'none';
        }
    }
    
    // Update all size select elements on page load
    document.querySelectorAll('select[id$="-size"]').forEach(select => {
        updateSizeTypeBadge(select);
        
        // Update on change
        select.addEventListener('change', function() {
            updateSizeTypeBadge(this);
        });
    });
    
    // Handle dynamically added rows
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes.length) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.querySelector) {
                        const newSelects = node.querySelectorAll('select[id$="-size"]');
                        newSelects.forEach(select => {
                            updateSizeTypeBadge(select);
                            select.addEventListener('change', function() {
                                updateSizeTypeBadge(this);
                            });
                        });
                    }
                });
            }
        });
    });
    
    // Start observing the document with the configured parameters
    observer.observe(document.body, { childList: true, subtree: true });
});
