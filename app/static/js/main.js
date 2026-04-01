// ── Toast ──
function showToast(msg, type='info') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show' + (type==='error' ? ' toast-error' : '');
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove('show'), 2800);
}

// ── Cart badge update ──
function updateBadge(count) {
  const b = document.getElementById('cart-badge');
  if (!b) return;
  b.textContent = count;
  b.style.display = count > 0 ? 'flex' : 'none';
}

// ── Add to Cart ──
async function addToCart(productId, btn, qty=1) {
  try {
    const res  = await fetch('/api/cart/add', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({product_id: productId, quantity: qty}),
    });
    const data = await res.json();
    updateBadge(data.count);
    showToast('Added to cart!');
    if (btn) { btn.textContent='Added'; btn.classList.add('in-cart'); btn.disabled=true; }
  } catch { showToast('Error adding item', 'error'); }
}

// ── Wishlist toggle ──
async function toggleWishlist(productId, btn) {
  try {
    const res  = await fetch('/api/wishlist/toggle', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({product_id: productId}),
    });
    const data = await res.json();
    if (data.error === 'login_required') {
      window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
      return;
    }
    if (data.action === 'added') {
      btn.classList.add('active'); btn.textContent = '❤️';
      showToast('Added to wishlist!');
    } else {
      btn.classList.remove('active'); btn.textContent = '🤍';
      showToast('Removed from wishlist');
      // If on wishlist page, remove the card
      const card = btn.closest('.product-card');
      if (card && window.location.pathname === '/wishlist') {
        card.style.opacity='0'; card.style.transform='scale(0.9)';
        setTimeout(()=> card.remove(), 300);
      }
    }
  } catch { showToast('Error. Please try again.', 'error'); }
}

// ── Password show/hide ──
function togglePwd(id, btn) {
  const inp = document.getElementById(id);
  if (inp.type === 'password') { inp.type='text'; btn.textContent='🙈'; }
  else { inp.type='password'; btn.textContent='👁️'; }
}

// ── User dropdown ──
function toggleUserMenu() {
  document.getElementById('userDropdown')?.classList.toggle('show');
}
document.addEventListener('click', e => {
  if (!e.target.closest('.user-menu'))
    document.getElementById('userDropdown')?.classList.remove('show');
});
