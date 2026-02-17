const messageBox = document.getElementById('message');
let activeFilters = {};

function showMessage(text, kind = 'success') {
  messageBox.textContent = text;
  messageBox.className = `message ${kind}`;
}

function toQuery(params) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && String(value).trim() !== '') {
      query.set(key, value);
    }
  });
  return query.toString();
}

async function fetchProducts(filters = {}) {
  const query = toQuery({ ...filters, status: 'approved' });
  const res = await fetch(`/api/products${query ? `?${query}` : ''}`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

async function fetchComparison(productId) {
  const res = await fetch(`/api/compare/${productId}`);
  if (!res.ok) return null;
  return res.json();
}

async function fetchOfferHistory(offerId) {
  const res = await fetch(`/api/offers/${offerId}/price-history`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

async function fetchProductCard(productId) {
  const res = await fetch(`/api/products/${productId}/card`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

async function fetchSellerDashboard(sellerName) {
  const encoded = encodeURIComponent(sellerName);
  const res = await fetch(`/api/sellers/${encoded}/dashboard`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

function renderProducts(products) {
  const target = document.getElementById('products');
  target.innerHTML = '';

  products.forEach(async (product) => {
    const cmp = await fetchComparison(product.id);
    const li = document.createElement('li');
    const price = cmp?.best_price_azn ? `${cmp.best_price_azn} AZN` : 'no approved offers yet';
    li.textContent = `#${product.id} ${product.title} (${product.condition}) — best price: ${price}`;
    target.appendChild(li);
  });
}

function renderPriceHistory(historyRows) {
  const target = document.getElementById('price-history');
  target.innerHTML = '';

  if (!historyRows.length) {
    const li = document.createElement('li');
    li.textContent = 'No price history yet';
    target.appendChild(li);
    return;
  }

  historyRows.forEach((row) => {
    const li = document.createElement('li');
    const oldPrice = row.old_price_azn === null ? 'initial' : `${row.old_price_azn} AZN`;
    li.textContent = `${row.changed_at}: ${oldPrice} -> ${row.new_price_azn} AZN`;
    target.appendChild(li);
  });
}

async function refreshProducts() {
  const products = await fetchProducts(activeFilters);
  renderProducts(products);
}

async function parseError(res) {
  try {
    const body = await res.json();
    return body.error || 'Unexpected error';
  } catch {
    return 'Unexpected error';
  }
}

document.getElementById('product-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.target;
  const payload = {
    title: form.title.value,
    brand: form.brand.value || null,
    category: form.category.value || null,
    condition: form.condition.value,
  };

  const res = await fetch('/api/products', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    showMessage(await parseError(res), 'error');
    return;
  }

  form.reset();
  showMessage('Product created');
  await refreshProducts();
});

document.getElementById('offer-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.target;
  const payload = {
    product_id: Number(form.product_id.value),
    seller: {
      name: form.seller_name.value,
      city: form.seller_city.value || null,
    },
    price_azn: Number(form.price_azn.value),
    url: form.url.value || null,
    currency: 'AZN',
    is_available: true,
  };

  const res = await fetch('/api/offers', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    showMessage(await parseError(res), 'error');
    return;
  }

  const created = await res.json();
  form.reset();
  showMessage(`Offer #${created.id} created with status: ${created.status}`);
  await refreshProducts();
});

document.getElementById('moderation-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.target;
  const offerId = Number(form.offer_id.value);
  const status = form.status.value;

  const res = await fetch(`/api/offers/${offerId}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  });

  if (!res.ok) {
    showMessage(await parseError(res), 'error');
    return;
  }

  const updated = await res.json();
  form.reset();
  showMessage(`Offer #${updated.id} status updated to ${updated.status}`);
  await refreshProducts();
});

document.getElementById('price-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.target;
  const offerId = Number(form.offer_id.value);
  const price = Number(form.price_azn.value);

  const res = await fetch(`/api/offers/${offerId}/price`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ price_azn: price }),
  });

  if (!res.ok) {
    showMessage(await parseError(res), 'error');
    return;
  }

  const updated = await res.json();
  form.reset();
  showMessage(`Offer #${updated.id} price updated to ${updated.price_azn} AZN`);
  await refreshProducts();
});

document.getElementById('load-history').addEventListener('click', async () => {
  const offerId = Number(document.getElementById('history-offer-id').value);
  if (!offerId) {
    showMessage('Provide offer id for history', 'error');
    return;
  }

  try {
    const rows = await fetchOfferHistory(offerId);
    renderPriceHistory(rows);
    showMessage(`Loaded ${rows.length} price history records`);
  } catch (error) {
    showMessage(String(error.message || error), 'error');
  }
});

document.getElementById('filter-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.target;
  activeFilters = {
    search: form.search.value || null,
    category: form.category.value || null,
    city: form.city.value || null,
    min_price: form.min_price.value || null,
    max_price: form.max_price.value || null,
    condition: form.condition.value || null,
  };

  try {
    await refreshProducts();
    showMessage('Filters applied');
  } catch (error) {
    showMessage(String(error.message || error), 'error');
  }
});

document.getElementById('load-card').addEventListener('click', async () => {
  const productId = Number(document.getElementById('card-product-id').value);
  if (!productId) {
    showMessage('Provide product id', 'error');
    return;
  }

  try {
    const card = await fetchProductCard(productId);
    document.getElementById('product-card').textContent = JSON.stringify(card, null, 2);
    showMessage('Product card loaded');
  } catch (error) {
    showMessage(String(error.message || error), 'error');
  }
});

document.getElementById('load-dashboard').addEventListener('click', async () => {
  const sellerName = document.getElementById('dashboard-seller-name').value.trim();
  if (!sellerName) {
    showMessage('Provide seller name', 'error');
    return;
  }

  try {
    const dashboard = await fetchSellerDashboard(sellerName);
    document.getElementById('seller-dashboard').textContent = JSON.stringify(dashboard, null, 2);
    showMessage('Seller dashboard loaded');
  } catch (error) {
    showMessage(String(error.message || error), 'error');
  }
});

document.getElementById('refresh').addEventListener('click', async () => {
  activeFilters = {};
  await refreshProducts();
  showMessage('Catalog refreshed');
});

refreshProducts();
