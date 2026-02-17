let activeFilters = {};

function toQuery(params) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== null && value !== undefined && String(value).trim() !== '') {
      query.set(key, value);
    }
  });
  return query.toString();
}

async function requestJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to load catalog');
  return res.json();
}

async function fetchProducts(filters = {}) {
  const query = toQuery({ ...filters, status: 'approved' });
  return requestJson(`/api/products${query ? `?${query}` : ''}`);
}

async function fetchProductCard(productId) {
  return requestJson(`/api/products/${productId}/card`);
}

function cardHtml(card) {
  const offers = card.offers.filter((offer) => offer.status === 'approved').slice(0, 3);
  const offersHtml = offers.length
    ? offers
        .map(
          (offer) => `<li><b>${offer.price_azn} ${offer.currency}</b> — ${offer.seller_name} (${offer.seller_city || 'N/A'})</li>`
        )
        .join('')
    : '<li>No approved offers</li>';

  return `
    <article class="product-card">
      <h3>${card.product.title}</h3>
      <p class="muted">${card.product.brand || 'Unknown brand'} · ${card.product.category || 'General'} · ${card.product.condition}</p>
      <p class="price">Best price: ${card.best_price_approved ? `${card.best_price_approved} AZN` : 'N/A'}</p>
      <ul>${offersHtml}</ul>
    </article>
  `;
}

async function renderCatalog() {
  const products = await fetchProducts(activeFilters);
  const grid = document.getElementById('catalog-grid');
  grid.innerHTML = '<p class="muted">Loading details…</p>';

  const cards = await Promise.all(
    products.map(async (product) => {
      try {
        return await fetchProductCard(product.id);
      } catch {
        return null;
      }
    })
  );

  const valid = cards.filter(Boolean);
  if (!valid.length) {
    grid.innerHTML = '<p class="muted">No products found.</p>';
    return;
  }

  grid.innerHTML = valid.map(cardHtml).join('');
}

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
  await renderCatalog();
});

renderCatalog();
