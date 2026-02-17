const msg = document.getElementById('admin-message');

function show(text, kind = 'success') {
  msg.textContent = text;
  msg.className = `message ${kind}`;
}

function toQuery(params) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && String(value).trim() !== '') q.set(key, value);
  });
  return q.toString();
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

function stagedCardHtml(product) {
  return `
    <article class="product-card">
      <h3>#${product.id} · ${product.title}</h3>
      <p class="muted">${product.brand || 'Unknown brand'} · ${product.category || 'General'} · ${product.condition}</p>
      <p class="muted">Source: ${product.source}${product.source_url ? ` · <a href="${product.source_url}" target="_blank" rel="noreferrer">link</a>` : ''}</p>
      <button type="button" data-publish-id="${product.id}">Publish</button>
    </article>
  `;
}

async function refreshStaged() {
  const products = await requestJson('/api/admin/staged/products');
  const grid = document.getElementById('staged-products-grid');
  if (!products.length) {
    grid.innerHTML = '<p class="muted">No staged products loaded</p>';
    return;
  }
  grid.innerHTML = products.map(stagedCardHtml).join('');
}

async function loadOffers(filters = {}) {
  const query = toQuery(filters);
  const offers = await requestJson(`/api/offers${query ? `?${query}` : ''}`);
  const tbody = document.getElementById('offers-table-body');
  if (!offers.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="muted">No offers found</td></tr>';
    return;
  }

  tbody.innerHTML = offers.map((offer) => `
    <tr>
      <td>${offer.id}</td>
      <td>${offer.title}</td>
      <td>${offer.seller_name}${offer.seller_city ? ` (${offer.seller_city})` : ''}</td>
      <td>
        <input type="number" min="1" step="0.01" value="${offer.price_azn}" data-price-id="${offer.id}" class="inline-input" />
      </td>
      <td><span class="status status-${offer.status}">${offer.status}</span></td>
      <td class="action-row">
        <button type="button" data-status-id="${offer.id}" data-status-value="approved">Approve</button>
        <button type="button" data-status-id="${offer.id}" data-status-value="rejected" class="secondary-btn">Reject</button>
        <button type="button" data-save-price-id="${offer.id}" class="ghost-btn">Save price</button>
      </td>
    </tr>
  `).join('');
}

document.getElementById('public-product-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const f = event.target;
  try {
    const created = await requestJson('/api/products', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: f.title.value,
        brand: f.brand.value || null,
        category: f.category.value || null,
        condition: f.condition.value,
      }),
    });
    show(`Public product #${created.id} created`);
    f.reset();
  } catch (e) {
    show(e.message, 'error');
  }
});

document.getElementById('public-offer-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const f = event.target;
  try {
    const created = await requestJson('/api/offers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        product_id: Number(f.product_id.value),
        seller: {
          name: f.seller_name.value,
          city: f.seller_city.value || null,
        },
        price_azn: Number(f.price_azn.value),
        currency: 'AZN',
        url: f.url.value || null,
        is_available: true,
      }),
    });
    show(`Public offer #${created.id} created as pending`);
    f.reset();
    await loadOffers({ status: 'pending' });
  } catch (e) {
    show(e.message, 'error');
  }
});

document.getElementById('stage-product-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const f = event.target;
  try {
    const created = await requestJson('/api/admin/staged/products', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        title: f.title.value,
        brand: f.brand.value || null,
        category: f.category.value || null,
        condition: f.condition.value,
        source: 'manual',
      }),
    });
    show(`Staged product #${created.id} created`);
    f.reset();
    await refreshStaged();
  } catch (e) {
    show(e.message, 'error');
  }
});

document.getElementById('stage-offer-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const f = event.target;
  try {
    const created = await requestJson('/api/admin/staged/offers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        staged_product_id: Number(f.staged_product_id.value),
        seller_name: f.seller_name.value,
        seller_city: f.seller_city.value || null,
        price_azn: Number(f.price_azn.value),
        currency: 'AZN',
        url: f.url.value || null,
      }),
    });
    show(`Staged offer #${created.id} created`);
    f.reset();
  } catch (e) {
    show(e.message, 'error');
  }
});

document.getElementById('parse-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const f = event.target;
  try {
    const result = await requestJson('/api/admin/staged/parse-url', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_url: f.source_url.value }),
    });
    show(`Parsed and staged: ${result.staged_products_created} products`);
    await refreshStaged();
  } catch (e) {
    show(e.message, 'error');
  }
});

document.getElementById('refresh-staged').addEventListener('click', async () => {
  try {
    await refreshStaged();
    show('Staged list refreshed');
  } catch (e) {
    show(e.message, 'error');
  }
});

document.getElementById('staged-products-grid').addEventListener('click', async (event) => {
  const id = event.target.getAttribute('data-publish-id');
  if (!id) return;

  try {
    const result = await requestJson(`/api/admin/staged/products/${Number(id)}/publish`, { method: 'POST' });
    show(`Published product #${result.published_product_id} with ${result.published_offers} offers`);
    await refreshStaged();
  } catch (e) {
    show(e.message, 'error');
  }
});

document.getElementById('moderation-filter-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const f = event.target;
  try {
    await loadOffers({
      status: f.status.value || null,
      seller_name: f.seller_name.value || null,
      city: f.city.value || null,
    });
  } catch (e) {
    show(e.message, 'error');
  }
});

document.getElementById('offers-table-body').addEventListener('click', async (event) => {
  const statusId = event.target.getAttribute('data-status-id');
  const statusValue = event.target.getAttribute('data-status-value');
  const savePriceId = event.target.getAttribute('data-save-price-id');

  try {
    if (statusId && statusValue) {
      await requestJson(`/api/offers/${Number(statusId)}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: statusValue }),
      });
      show(`Offer #${statusId} moved to ${statusValue}`);
      document.getElementById('moderation-filter-form').dispatchEvent(new Event('submit'));
      return;
    }

    if (savePriceId) {
      const input = document.querySelector(`[data-price-id="${savePriceId}"]`);
      const price = Number(input.value);
      await requestJson(`/api/offers/${Number(savePriceId)}/price`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ price_azn: price }),
      });
      show(`Price for offer #${savePriceId} updated`);
      return;
    }
  } catch (e) {
    show(e.message, 'error');
  }
});

refreshStaged();
loadOffers({ status: 'pending' });
