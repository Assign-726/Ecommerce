// ------------------------------
// Cart Coupon Frontend (Reset)
// ------------------------------

// Show a coupon message under the input
function showCouponMessage(message, type = 'success') {
    const couponMessage = document.getElementById('coupon-message');
    if (!couponMessage) return;
    couponMessage.textContent = message || '';
    couponMessage.className = 'mt-1 text-sm ' + (type === 'success' ? 'text-green-600' : 'text-red-600');
}

// Optional: live validate coupon (uses cart:validate_coupon => GET ?code=)
function validateCoupon(code) {
    if (!code) return;
    fetch(`/cart/coupon/validate/?code=${encodeURIComponent(code)}`, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(r => r.json())
    .then(data => {
        if (data.valid) {
            showCouponMessage(data.message || 'Coupon looks valid', 'success');
        } else {
            showCouponMessage(data.message || 'Invalid coupon code', 'error');
        }
    })
    .catch(() => {
        // Silent fail for live validation
    });
}

// Apply coupon via POST to cart:apply_coupon
function handleCouponSubmit(e) {
    e.preventDefault();
    e.stopPropagation();

    const form = e.target;
    const formData = new FormData(form);
    const submitButton = form.querySelector('button[type="submit"]');
    const originalButtonText = submitButton.innerHTML;
    const csrfToken = formData.get('csrfmiddlewaretoken') || document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

    // Normalize code to uppercase
    if (formData.get('coupon_code')) {
        formData.set('coupon_code', String(formData.get('coupon_code')).trim().toUpperCase());
    }

    submitButton.disabled = true;
    submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> Applying...';
    showCouponMessage('');

    fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': csrfToken,
            'Accept': 'application/json'
        },
        credentials: 'same-origin'
    })
    .then(response => response.json())
    .then(data => {
        if (data.valid) {
            showCouponMessage(data.message || 'Coupon applied successfully!', 'success');

            if (data.order_summary_html) {
                const container = document.getElementById('order-summary-container');
                if (container) {
                    const y = window.scrollY;
                    container.outerHTML = data.order_summary_html;
                    // Re-bind events for new DOM
                    initializeCart();
                    window.scrollTo(0, y);
                    return;
                }
            }
            // Fallback
            window.location.reload();
        } else {
            showCouponMessage(data.message || 'Invalid coupon code', 'error');
        }
    })
    .catch(err => {
        console.error('Apply coupon error:', err);
        showCouponMessage('An error occurred. Please try again.', 'error');
    })
    .finally(() => {
        submitButton.disabled = false;
        submitButton.innerHTML = originalButtonText;
    });
}

// Remove coupon via POST to cart:remove_coupon
function handleRemoveCoupon(e) {
    e.preventDefault();
    const form = e.target;
    const btn = form.querySelector('button[type="submit"]');
    const original = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> Removing...';

    fetch(form.action, {
        method: 'POST',
        headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]')?.value || ''
        },
        credentials: 'same-origin'
    })
    .then(r => r.json())
    .then(data => {
        if (data.valid && data.order_summary_html) {
            const container = document.getElementById('order-summary-container');
            if (container) {
                container.outerHTML = data.order_summary_html;
                initializeCart();
                return;
            }
        }
        // Fallbacks
        if (data.success) {
            window.location.reload();
        } else if (data.redirect) {
            window.location.href = data.redirect;
        } else {
            window.location.reload();
        }
    })
    .catch(err => {
        console.error('Remove coupon error:', err);
        showCouponMessage('Failed to remove coupon. Please try again.', 'error');
    })
    .finally(() => {
        btn.disabled = false;
        btn.innerHTML = original;
    });
}

// Bind listeners for current DOM
function initializeCart() {
    const applyForm = document.getElementById('apply-coupon-form');
    const removeForm = document.getElementById('remove-coupon-form');
    const couponInput = document.getElementById('coupon-code');

    if (applyForm) {
        // Avoid duplicate handlers
        applyForm.removeEventListener('submit', handleCouponSubmit);
        applyForm.addEventListener('submit', handleCouponSubmit);
    }

    if (removeForm) {
        removeForm.removeEventListener('submit', handleRemoveCoupon);
        removeForm.addEventListener('submit', handleRemoveCoupon);
    }

    if (couponInput) {
        let debounceTimer;
        couponInput.addEventListener('input', function() {
            clearTimeout(debounceTimer);
            const code = this.value.trim();
            if (code.length < 3) return;
            debounceTimer = setTimeout(() => validateCoupon(code), 500);
        });
    }

    // Removed MutationObserver guard to prevent unintended reloads
}

// Init on load
document.addEventListener('DOMContentLoaded', function() {
    initializeCart();
});
