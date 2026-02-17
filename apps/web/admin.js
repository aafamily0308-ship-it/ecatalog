const msg = document.getElementById('admin-message');

function show(text, kind = 'success') {
  msg.textContent = text;
  msg.className = `message ${kind}`;
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

async function refreshStaged() {
  const products = await requestJson('/api/admin/staged/products');
  document.getElementById('staged-products-box').textContent = JSON.stringify(products, null, 2);
}

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

document.getElementById('publish-form').addEventListener('submit', async (event) => {
  event.preventDefault();
  const f = event.target;
  try {
    const stagedId = Number(f.staged_product_id.value);
    const result = await requestJson(`/api/admin/staged/products/${stagedId}/publish`, { method: 'POST' });
    show(`Published product #${result.published_product_id} with ${result.published_offers} offers`);
    f.reset();
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

refreshStaged();
