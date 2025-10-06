// Wishlist page interactions
(function () {
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  }

  window.removeFromWishlist = function (productId) {
    if (!confirm('Remove this item from your wishlist?')) {
      return;
    }

    const csrfTokenField = document.querySelector('[name=csrfmiddlewaretoken]');
    const csrfToken = csrfTokenField ? csrfTokenField.value : (getCookie('csrftoken') || '');

    fetch(`/wishlist/remove/${productId}/`, {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrfToken,
        'X-Requested-With': 'XMLHttpRequest',
      },
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          // Reload page to update list and navbar wishlist count
          location.reload();
        } else {
          alert(data.message || 'Failed to remove item.');
        }
      })
      .catch((error) => {
        console.error('Error:', error);
        alert('An error occurred. Please try again.');
      });
  };
})();
