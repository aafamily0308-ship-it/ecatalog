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

async function parseError(res) {
  try {
    const body = await res.json();
    return body.error || 'Unexpected error';
  } catch {
    return 'Unexpected error';
  }
}

async function requestJson(url, opts = {}) {
  const res = await fetch(url, opts);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

async function fetchProducts(filters = {}) {
  const query = toQuery({ ...filters, status: 'approved' });
  return requestJson(`/api/products${query ? `?${query}` : ''}`);
}

async function fetchComparison(productId) {
  const res = await fetch(`/api/compare/${productId}`);
  if (!res.ok) return null;
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

document.getElementById('product-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.target;
  try {
    await requestJson('/api/products', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: form.title.value, brand: form.brand.value || null, category: form.category.value || null, condition: form.condition.value }),
    });
    form.reset(); showMessage('Product created'); await refreshProducts();
  } catch (e) { showMessage(e.message, 'error'); }
});

document.getElementById('offer-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.target;
  try {
    const created = await requestJson('/api/offers', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        product_id: Number(form.product_id.value),
        seller: { name: form.seller_name.value, city: form.seller_city.value || null },
        price_azn: Number(form.price_azn.value), url: form.url.value || null, currency: 'AZN', is_available: true,
      }),
    });
    form.reset(); showMessage(`Offer #${created.id} created with status: ${created.status}`); await refreshProducts();
  } catch (e) { showMessage(e.message, 'error'); }
});

document.getElementById('moderation-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.target;
  try {
    const updated = await requestJson(`/api/offers/${Number(form.offer_id.value)}/status`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status: form.status.value }),
    });
    form.reset(); showMessage(`Offer #${updated.id} status updated to ${updated.status}`); await refreshProducts();
  } catch (e) { showMessage(e.message, 'error'); }
});

document.getElementById('price-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.target;
  try {
    const updated = await requestJson(`/api/offers/${Number(form.offer_id.value)}/price`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ price_azn: Number(form.price_azn.value) }),
    });
    form.reset(); showMessage(`Offer #${updated.id} price updated to ${updated.price_azn} AZN`); await refreshProducts();
  } catch (e) { showMessage(e.message, 'error'); }
});

document.getElementById('load-history').addEventListener('click', async () => {
  const offerId = Number(document.getElementById('history-offer-id').value);
  if (!offerId) return showMessage('Provide offer id for history', 'error');
  try { renderPriceHistory(await requestJson(`/api/offers/${offerId}/price-history`)); showMessage('Price history loaded'); }
  catch (e) { showMessage(e.message, 'error'); }
});

document.getElementById('verify-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.target;
  try {
    const seller = await requestJson(`/api/sellers/${encodeURIComponent(form.seller_name.value)}/verify`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ verification_level: form.verification_level.value }),
    });
    showMessage(`Seller ${seller.name} verification: ${seller.verification_level}`);
  } catch (e) { showMessage(e.message, 'error'); }
});

document.getElementById('review-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.target;
  try {
    const res = await requestJson(`/api/sellers/${encodeURIComponent(form.seller_name.value)}/reviews`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reviewer_name: form.reviewer_name.value, score: Number(form.score.value), comment: form.comment.value || null }),
    });
    showMessage(`Review added. Seller rating: ${res.seller.rating} (${res.seller.review_count})`);
    form.reset();
  } catch (e) { showMessage(e.message, 'error'); }
});

document.getElementById('alert-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.target;
  try {
    const alert = await requestJson('/api/alerts', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product_id: Number(form.product_id.value), target_price_azn: Number(form.target_price_azn.value), contact_email: form.contact_email.value }),
    });
    showMessage(`Alert #${alert.id} created`); form.reset();
  } catch (e) { showMessage(e.message, 'error'); }
});

document.getElementById('fraud-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.target;
  try {
    const signal = await requestJson('/api/fraud-signals', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        offer_id: form.offer_id.value ? Number(form.offer_id.value) : null,
        seller_name: form.seller_name.value || null,
        signal_type: form.signal_type.value,
        risk_score: Number(form.risk_score.value),
        details: form.details.value || null,
      }),
    });
    showMessage(`Fraud signal #${signal.id} created`); form.reset();
  } catch (e) { showMessage(e.message, 'error'); }
});

document.getElementById('filter-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.target;
  activeFilters = { search: form.search.value || null, category: form.category.value || null, city: form.city.value || null, min_price: form.min_price.value || null, max_price: form.max_price.value || null, condition: form.condition.value || null };
  try { await refreshProducts(); showMessage('Filters applied'); } catch (e) { showMessage(e.message, 'error'); }
});

document.getElementById('load-card').addEventListener('click', async () => {
  const productId = Number(document.getElementById('card-product-id').value);
  if (!productId) return showMessage('Provide product id', 'error');
  try { document.getElementById('product-card').textContent = JSON.stringify(await requestJson(`/api/products/${productId}/card`), null, 2); showMessage('Product card loaded'); }
  catch (e) { showMessage(e.message, 'error'); }
});

document.getElementById('load-dashboard').addEventListener('click', async () => {
  const seller = document.getElementById('dashboard-seller-name').value.trim();
  if (!seller) return showMessage('Provide seller name', 'error');
  try { document.getElementById('seller-dashboard').textContent = JSON.stringify(await requestJson(`/api/sellers/${encodeURIComponent(seller)}/dashboard`), null, 2); showMessage('Seller dashboard loaded'); }
  catch (e) { showMessage(e.message, 'error'); }
});

document.getElementById('load-reviews').addEventListener('click', async () => {
  const seller = document.getElementById('reviews-seller-name').value.trim();
  if (!seller) return showMessage('Provide seller name', 'error');
  try { document.getElementById('seller-reviews').textContent = JSON.stringify(await requestJson(`/api/sellers/${encodeURIComponent(seller)}/reviews`), null, 2); showMessage('Reviews loaded'); }
  catch (e) { showMessage(e.message, 'error'); }
});

document.getElementById('load-alerts').addEventListener('click', async () => {
  const email = document.getElementById('alerts-email').value.trim();
  const query = email ? `?${toQuery({ contact_email: email })}` : '';
  try { document.getElementById('alerts-box').textContent = JSON.stringify(await requestJson(`/api/alerts${query}`), null, 2); showMessage('Alerts loaded'); }
  catch (e) { showMessage(e.message, 'error'); }
});

document.getElementById('load-fraud').addEventListener('click', async () => {
  const minRisk = document.getElementById('fraud-min-risk').value;
  const query = minRisk ? `?${toQuery({ min_risk_score: minRisk })}` : '';
  try { document.getElementById('fraud-box').textContent = JSON.stringify(await requestJson(`/api/fraud-signals${query}`), null, 2); showMessage('Fraud signals loaded'); }
  catch (e) { showMessage(e.message, 'error'); }
});

document.getElementById('refresh').addEventListener('click', async () => {
  activeFilters = {};
  await refreshProducts();
  showMessage('Catalog refreshed');
});

refreshProducts();
