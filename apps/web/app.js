const messageBox = document.getElementById('message');

function showMessage(text, kind = 'success') {
  messageBox.textContent = text;
  messageBox.className = `message ${kind}`;
}

async function fetchProducts() {
  const res = await fetch('/api/products');
  return res.json();
}

async function fetchComparison(productId) {
  const res = await fetch(`/api/compare/${productId}`);
  if (!res.ok) return null;
  return res.json();
}

async function fetchOfferHistory(offerId) {
  const res = await fetch(`/api/offers/${offerId}/price-history`);
  if (!res.ok) {
    throw new Error(await parseError(res));
  }
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
  const products = await fetchProducts();
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

document.getElementById('refresh').addEventListener('click', refreshProducts);
refreshProducts();
